"""Tree-sitter source chunking with sliding-window fallbacks."""

from __future__ import annotations

import hashlib
import importlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

ChunkType = Literal["function", "class", "module"]


@dataclass(frozen=True, slots=True)
class CodeChunk:
    """A searchable source code chunk."""

    content: str
    file_path: str
    start_line: int
    end_line: int
    chunk_type: ChunkType
    language: str
    name: str
    id: str
    repo_id: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, str | int]:
        """Return Chroma-compatible metadata."""
        return {
            "repo_id": self.repo_id,
            "file_path": self.file_path,
            "language": self.language,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "chunk_type": self.chunk_type,
            "name": self.name,
            **dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class _LanguageSpec:
    """Tree-sitter language metadata."""

    name: str
    parser_name: str


@dataclass(frozen=True, slots=True)
class _Token:
    """Token with line-position metadata for fallback chunking."""

    value: str
    line_number: int


class TreeSitterParseError(RuntimeError):
    """Raised when Tree-sitter cannot parse a supported source file."""


class CodeChunker:
    """Chunk source files at function/class level when Tree-sitter parsers are available."""

    _LANGUAGE_BY_EXTENSION: dict[str, _LanguageSpec] = {
        ".py": _LanguageSpec(name="python", parser_name="python"),
        ".js": _LanguageSpec(name="javascript", parser_name="javascript"),
        ".jsx": _LanguageSpec(name="javascript", parser_name="javascript"),
        ".ts": _LanguageSpec(name="typescript", parser_name="typescript"),
        ".tsx": _LanguageSpec(name="typescript", parser_name="tsx"),
        ".java": _LanguageSpec(name="java", parser_name="java"),
        ".go": _LanguageSpec(name="go", parser_name="go"),
        ".rs": _LanguageSpec(name="rust", parser_name="rust"),
        ".c": _LanguageSpec(name="c", parser_name="c"),
        ".h": _LanguageSpec(name="c", parser_name="c"),
        ".cpp": _LanguageSpec(name="cpp", parser_name="cpp"),
        ".cc": _LanguageSpec(name="cpp", parser_name="cpp"),
        ".cxx": _LanguageSpec(name="cpp", parser_name="cpp"),
        ".hpp": _LanguageSpec(name="cpp", parser_name="cpp"),
        ".rb": _LanguageSpec(name="ruby", parser_name="ruby"),
    }
    _TEXT_LANGUAGE_BY_EXTENSION: dict[str, str] = {
        ".md": "markdown",
        ".markdown": "markdown",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".txt": "text",
    }
    _FUNCTION_NODE_TYPES: dict[str, set[str]] = {
        "python": {"function_definition"},
        "javascript": {
            "arrow_function",
            "function",
            "function_declaration",
            "function_expression",
            "generator_function_declaration",
            "method_definition",
        },
        "typescript": {
            "abstract_method_signature",
            "arrow_function",
            "function",
            "function_declaration",
            "function_expression",
            "generator_function_declaration",
            "method_definition",
            "method_signature",
        },
        "java": {"constructor_declaration", "method_declaration"},
        "go": {"function_declaration", "method_declaration"},
        "rust": {"function_item"},
        "c": {"function_definition"},
        "cpp": {"function_definition"},
        "ruby": {"method", "singleton_method"},
    }
    _CLASS_NODE_TYPES: dict[str, set[str]] = {
        "python": {"class_definition"},
        "javascript": {"class", "class_declaration"},
        "typescript": {"abstract_class_declaration", "class", "class_declaration"},
        "java": {"class_declaration", "enum_declaration", "interface_declaration", "record_declaration"},
        "go": {"type_declaration", "type_spec"},
        "rust": {"enum_item", "impl_item", "struct_item", "trait_item"},
        "c": {"struct_specifier", "union_specifier"},
        "cpp": {"class_specifier", "struct_specifier", "union_specifier"},
        "ruby": {"class"},
    }
    _MODULE_NODE_TYPES: dict[str, set[str]] = {
        "ruby": {"module"},
    }
    _INDIVIDUAL_LANGUAGE_PACKAGES: dict[str, tuple[str, str]] = {
        "python": ("tree_sitter_python", "language"),
        "javascript": ("tree_sitter_javascript", "language"),
        "typescript": ("tree_sitter_typescript", "language_typescript"),
        "tsx": ("tree_sitter_typescript", "language_tsx"),
        "java": ("tree_sitter_java", "language"),
        "go": ("tree_sitter_go", "language"),
        "rust": ("tree_sitter_rust", "language"),
        "c": ("tree_sitter_c", "language"),
        "cpp": ("tree_sitter_cpp", "language"),
        "ruby": ("tree_sitter_ruby", "language"),
    }

    def __init__(
        self,
        fallback_window_tokens: int = 512,
        fallback_overlap_tokens: int = 64,
        unsupported_window_tokens: int = 256,
        unsupported_overlap_tokens: int = 32,
    ) -> None:
        self.fallback_window_tokens = fallback_window_tokens
        self.fallback_overlap_tokens = fallback_overlap_tokens
        self.unsupported_window_tokens = unsupported_window_tokens
        self.unsupported_overlap_tokens = unsupported_overlap_tokens
        self._language_cache: dict[str, Any] = {}

    def chunk_file(self, repo_id: str, root: Path, file_path: Path) -> list[CodeChunk]:
        """Chunk a file relative to a repository root."""
        relative_path = self._relative_path(root, file_path)
        text = file_path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            return []

        language_spec = self._LANGUAGE_BY_EXTENSION.get(file_path.suffix.lower())
        if language_spec is None:
            return self._sliding_window_chunks(
                repo_id=repo_id,
                relative_path=relative_path,
                text=text,
                language=self.detect_language(file_path),
                window_tokens=self.unsupported_window_tokens,
                overlap_tokens=self.unsupported_overlap_tokens,
            )

        try:
            return self._tree_sitter_chunks(
                repo_id=repo_id,
                relative_path=relative_path,
                text=text,
                language_spec=language_spec,
            )
        except TreeSitterParseError:
            return self._sliding_window_chunks(
                repo_id=repo_id,
                relative_path=relative_path,
                text=text,
                language=language_spec.name,
                window_tokens=self.fallback_window_tokens,
                overlap_tokens=self.fallback_overlap_tokens,
            )

    def detect_language(self, file_path: Path) -> str:
        """Return the normalized language name for a file extension."""
        suffix = file_path.suffix.lower()
        language_spec = self._LANGUAGE_BY_EXTENSION.get(suffix)
        if language_spec is not None:
            return language_spec.name
        return self._TEXT_LANGUAGE_BY_EXTENSION.get(suffix, "text")

    def _tree_sitter_chunks(
        self,
        repo_id: str,
        relative_path: str,
        text: str,
        language_spec: _LanguageSpec,
    ) -> list[CodeChunk]:
        source_bytes = text.encode("utf-8")
        try:
            parser = self._get_parser(language_spec.parser_name)
            tree = parser.parse(source_bytes)
        except Exception as exc:
            raise TreeSitterParseError(f"Tree-sitter failed for {relative_path}") from exc

        root_node = tree.root_node
        if bool(getattr(root_node, "has_error", False)):
            raise TreeSitterParseError(f"Tree-sitter reported parse errors for {relative_path}")

        chunks: list[CodeChunk] = []
        for node in self._walk_named_nodes(root_node):
            chunk_type = self._chunk_type(language_spec.name, node)
            if chunk_type is None:
                continue

            start_line = int(node.start_point[0]) + 1
            end_line = int(node.end_point[0]) + 1
            content = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
            name = self._node_name(node, source_bytes, chunk_type)
            chunks.append(
                self._build_chunk(
                    repo_id=repo_id,
                    relative_path=relative_path,
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_type=chunk_type,
                    language=language_spec.name,
                    name=name,
                ),
            )

        if chunks:
            return chunks

        return [
            self._build_chunk(
                repo_id=repo_id,
                relative_path=relative_path,
                content=text,
                start_line=1,
                end_line=max(1, len(text.splitlines())),
                chunk_type="module",
                language=language_spec.name,
                name=Path(relative_path).name,
            ),
        ]

    def _get_parser(self, parser_name: str) -> Any:
        try:
            from tree_sitter import Parser
        except ImportError as exc:
            raise TreeSitterParseError("The tree_sitter package is not installed.") from exc

        parser = Parser()
        language = self._load_language(parser_name)
        try:
            if hasattr(parser, "set_language"):
                parser.set_language(language)
            else:
                parser.language = language
        except (AttributeError, TypeError, ValueError) as exc:
            raise TreeSitterParseError(f"Could not configure parser '{parser_name}'.") from exc
        return parser

    def _load_language(self, parser_name: str) -> Any:
        cached = self._language_cache.get(parser_name)
        if cached is not None:
            return cached

        language = self._load_from_language_bundle(parser_name)
        if language is None:
            language = self._load_from_individual_package(parser_name)
        if language is None:
            raise TreeSitterParseError(
                f"No Tree-sitter grammar is installed for parser '{parser_name}'.",
            )

        self._language_cache[parser_name] = language
        return language

    def _load_from_language_bundle(self, parser_name: str) -> Any | None:
        for package_name in ("tree_sitter_languages", "tree_sitter_language_pack"):
            try:
                package = importlib.import_module(package_name)
                get_language = getattr(package, "get_language")
                return get_language(parser_name)
            except (ImportError, AttributeError, LookupError, TypeError):
                continue
        return None

    def _load_from_individual_package(self, parser_name: str) -> Any | None:
        package_info = self._INDIVIDUAL_LANGUAGE_PACKAGES.get(parser_name)
        if package_info is None:
            return None

        package_name, factory_name = package_info
        try:
            from tree_sitter import Language

            package = importlib.import_module(package_name)
            raw_language = getattr(package, factory_name)()
            try:
                return Language(raw_language)
            except TypeError:
                return raw_language
        except (ImportError, AttributeError, TypeError):
            return None

    def _walk_named_nodes(self, root_node: Any) -> list[Any]:
        nodes: list[Any] = []
        stack = [root_node]
        while stack:
            node = stack.pop()
            nodes.append(node)
            named_children = list(getattr(node, "named_children", []))
            stack.extend(reversed(named_children))
        return nodes

    def _chunk_type(self, language: str, node: Any) -> ChunkType | None:
        node_type = str(node.type)
        if node_type in self._MODULE_NODE_TYPES.get(language, set()):
            return "module"
        if node_type in self._CLASS_NODE_TYPES.get(language, set()):
            return "class"
        if node_type in self._FUNCTION_NODE_TYPES.get(language, set()):
            if (
                language in {"javascript", "typescript"}
                and node_type in {"arrow_function", "function", "function_expression"}
                and str(getattr(getattr(node, "parent", None), "type", "")) == "variable_declarator"
            ):
                return None
            return "function"
        if language in {"javascript", "typescript"} and node_type == "variable_declarator":
            if self._contains_function_expression(node):
                return "function"
        return None

    def _contains_function_expression(self, node: Any) -> bool:
        function_like = {"arrow_function", "function", "function_expression"}
        return any(str(child.type) in function_like for child in getattr(node, "named_children", []))

    def _node_name(self, node: Any, source_bytes: bytes, chunk_type: ChunkType) -> str:
        name_node = node.child_by_field_name("name")
        if name_node is None and str(node.type) in {"function_definition", "function_item"}:
            name_node = self._first_named_child_of_type(node, {"identifier"})
        if name_node is None:
            name_node = self._first_named_child_of_type(
                node,
                {"constant", "identifier", "property_identifier", "type_identifier"},
            )
        if name_node is None:
            parent = getattr(node, "parent", None)
            if parent is not None:
                name_node = parent.child_by_field_name("name")

        if name_node is None:
            line_number = int(node.start_point[0]) + 1
            return f"{chunk_type}_{line_number}"

        raw_name = source_bytes[name_node.start_byte : name_node.end_byte].decode(
            "utf-8",
            errors="replace",
        )
        return raw_name.strip() or f"{chunk_type}_{int(node.start_point[0]) + 1}"

    def _first_named_child_of_type(self, node: Any, node_types: set[str]) -> Any | None:
        for child in getattr(node, "named_children", []):
            if str(child.type) in node_types:
                return child
        return None

    def _sliding_window_chunks(
        self,
        repo_id: str,
        relative_path: str,
        text: str,
        language: str,
        window_tokens: int,
        overlap_tokens: int,
    ) -> list[CodeChunk]:
        tokens = self._tokens_with_lines(text)
        if not tokens:
            return []

        chunks: list[CodeChunk] = []
        step = max(1, window_tokens - overlap_tokens)
        lines = text.splitlines()
        for token_start in range(0, len(tokens), step):
            token_end = min(token_start + window_tokens, len(tokens))
            start_line = tokens[token_start].line_number
            end_line = tokens[token_end - 1].line_number
            content = "\n".join(lines[start_line - 1 : end_line])
            chunks.append(
                self._build_chunk(
                    repo_id=repo_id,
                    relative_path=relative_path,
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    chunk_type="module",
                    language=language,
                    name=Path(relative_path).name,
                ),
            )
            if token_end >= len(tokens):
                break
        return chunks

    def _tokens_with_lines(self, text: str) -> list[_Token]:
        tokens: list[_Token] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in re.finditer(r"\S+", line):
                tokens.append(_Token(value=match.group(0), line_number=line_number))
        return tokens

    def _build_chunk(
        self,
        repo_id: str,
        relative_path: str,
        content: str,
        start_line: int,
        end_line: int,
        chunk_type: ChunkType,
        language: str,
        name: str,
    ) -> CodeChunk:
        chunk_hash = hashlib.sha256(
            f"{repo_id}:{relative_path}:{start_line}:{end_line}:{chunk_type}:{name}".encode("utf-8"),
        ).hexdigest()[:12]
        return CodeChunk(
            id=f"{repo_id}:{relative_path}:{start_line}-{end_line}:{chunk_hash}",
            repo_id=repo_id,
            file_path=relative_path,
            start_line=start_line,
            end_line=end_line,
            chunk_type=chunk_type,
            language=language,
            name=name,
            content=content,
        )

    def _relative_path(self, root: Path, file_path: Path) -> str:
        try:
            return file_path.relative_to(root).as_posix()
        except ValueError:
            return file_path.as_posix()


class TreeSitterChunker(CodeChunker):
    """Backward-compatible name for earlier scaffold code."""

    def __init__(self, max_lines: int = 80, overlap_lines: int = 10) -> None:
        super().__init__(
            fallback_window_tokens=max_lines,
            fallback_overlap_tokens=overlap_lines,
            unsupported_window_tokens=max_lines,
            unsupported_overlap_tokens=overlap_lines,
        )


__all__ = ["ChunkType", "CodeChunk", "CodeChunker", "TreeSitterChunker", "TreeSitterParseError"]
