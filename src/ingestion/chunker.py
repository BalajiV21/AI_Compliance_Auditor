"""
Semantic chunking module for document processing
Implements intelligent chunking strategies with overlap and metadata preservation
"""
import re
from typing import List, Dict
from dataclasses import dataclass
from loguru import logger


@dataclass
class Chunk:
    """Represents a document chunk"""
    content: str
    metadata: Dict
    chunk_id: str
    start_char: int
    end_char: int


class SemanticChunker:
    """
    Intelligent document chunking with semantic awareness
    Preserves section headers, maintains context, and creates overlapping chunks
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ):
        """
        Initialize chunker

        Args:
            chunk_size: Target size for each chunk in characters
            chunk_overlap: Number of overlapping characters between chunks
            separators: List of separators for splitting (in priority order)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if separators is None:
            # Priority order: double newline (paragraphs), sections, single newline, sentences
            self.separators = [
                "\n\n\n",  # Section breaks
                "\n\n",    # Paragraph breaks
                "\n",      # Line breaks
                ". ",      # Sentence breaks
                ", ",      # Clause breaks
                " "        # Word breaks
            ]
        else:
            self.separators = separators

    def chunk_document(self, document: Dict) -> List[Chunk]:
        """
        Chunk a document into semantically meaningful pieces

        Args:
            document: Document dictionary with 'text' and 'metadata' keys

        Returns:
            List of Chunk objects
        """
        text = document['text']
        metadata = document['metadata']

        logger.info(f"Chunking document: {metadata.get('filename', 'unknown')}")

        # Extract sections if present (for regulatory documents)
        sections = self._extract_sections(text)

        chunks = []
        chunk_counter = 0

        if sections:
            # Chunk each section separately to preserve context
            for section_name, section_text in sections:
                section_chunks = self._chunk_text(
                    section_text,
                    metadata,
                    section_name=section_name,
                    start_id=chunk_counter
                )
                chunks.extend(section_chunks)
                chunk_counter += len(section_chunks)
        else:
            # Chunk entire document
            chunks = self._chunk_text(text, metadata, start_id=0)

        logger.info(f"Created {len(chunks)} chunks")
        return chunks

    def _extract_sections(self, text: str) -> List[tuple]:
        """
        Extract sections from regulatory documents
        Looks for patterns like "Article 17", "Section 164.502", etc.
        """
        sections = []

        # Patterns for common section headers
        patterns = [
            r'(Article \d+[.\d]*\s*-\s*[^\n]+)',  # GDPR style
            r'(Section \d+[.\d]*\s*-\s*[^\n]+)',  # HIPAA style
            r'(CC\d+\.\d+\s*-\s*[^\n]+)',         # SOC2 style
            r'([A-Z][A-Z\s]{10,}[\n])',           # ALL CAPS headers
            r'(={10,}[\n][^\n]+[\n]={10,})',      # Underlined headers
        ]

        # Try to find section markers
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            section_positions = [(m.start(), m.group(1)) for m in matches]

            if len(section_positions) > 2:  # At least a few sections found
                # Extract text for each section
                for i, (pos, header) in enumerate(section_positions):
                    start = pos
                    end = section_positions[i + 1][0] if i + 1 < len(section_positions) else len(text)
                    section_text = text[start:end]
                    sections.append((header.strip(), section_text))

                return sections

        return []

    def _chunk_text(
        self,
        text: str,
        metadata: Dict,
        section_name: str = None,
        start_id: int = 0
    ) -> List[Chunk]:
        """
        Chunk text using recursive splitting

        Args:
            text: Text to chunk
            metadata: Document metadata
            section_name: Name of the section (if applicable)
            start_id: Starting chunk ID

        Returns:
            List of Chunk objects
        """
        chunks = []
        start_pos = 0
        chunk_id = start_id

        while start_pos < len(text):
            # Calculate end position for this chunk
            end_pos = min(start_pos + self.chunk_size, len(text))

            # Try to find a good breaking point
            if end_pos < len(text):
                chunk_text = text[start_pos:end_pos]

                # Try each separator to find the best split point
                best_split = end_pos
                for separator in self.separators:
                    last_sep = chunk_text.rfind(separator)
                    if last_sep != -1:
                        best_split = start_pos + last_sep + len(separator)
                        break

                end_pos = best_split

            # Extract chunk content
            chunk_content = text[start_pos:end_pos].strip()

            if chunk_content:  # Only add non-empty chunks
                # Create chunk metadata
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = chunk_id
                chunk_metadata['start_char'] = start_pos
                chunk_metadata['end_char'] = end_pos

                if section_name:
                    chunk_metadata['section'] = section_name

                # Create chunk ID
                doc_id = metadata.get('filename', 'unknown').replace('.', '_')
                chunk_identifier = f"{doc_id}_chunk_{chunk_id}"

                chunks.append(Chunk(
                    content=chunk_content,
                    metadata=chunk_metadata,
                    chunk_id=chunk_identifier,
                    start_char=start_pos,
                    end_char=end_pos
                ))

                chunk_id += 1

            # Move to next chunk with overlap
            start_pos = end_pos - self.chunk_overlap

            # Ensure we make progress
            if start_pos >= end_pos:
                start_pos = end_pos

        return chunks

    def chunk_with_context(self, document: Dict, context_window: int = 100) -> List[Chunk]:
        """
        Create chunks with additional context from surrounding text

        Args:
            document: Document dictionary
            context_window: Number of characters to include as context

        Returns:
            List of Chunk objects with context
        """
        chunks = self.chunk_document(document)

        # Add context to each chunk
        for i, chunk in enumerate(chunks):
            context_before = ""
            context_after = ""

            # Get context from previous chunk
            if i > 0:
                prev_chunk = chunks[i - 1]
                context_before = prev_chunk.content[-context_window:]

            # Get context from next chunk
            if i < len(chunks) - 1:
                next_chunk = chunks[i + 1]
                context_after = next_chunk.content[:context_window]

            # Add context to metadata
            chunk.metadata['context_before'] = context_before
            chunk.metadata['context_after'] = context_after

        return chunks


class RegulationChunker(SemanticChunker):
    """
    Specialized chunker for regulatory documents
    Preserves article/section structure and legal references
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        super().__init__(chunk_size, chunk_overlap)

        # Regulatory-specific separators
        self.separators = [
            "\n\n========================================\n",  # Major sections
            "\n\n\n",  # Section breaks
            "\n\n",    # Paragraph breaks
            "\n",      # Line breaks
            "; ",      # List items in regulations
            ". ",      # Sentence breaks
            " "        # Word breaks
        ]

    def extract_legal_references(self, text: str) -> List[str]:
        """
        Extract legal references from text
        E.g., "Article 17", "Section 164.502"
        """
        patterns = [
            r'Article \d+[.\d]*',
            r'Section \d+[.\d]*',
            r'CC\d+\.\d+',
            r'Regulation \([A-Z]+\) \d+/\d+',
        ]

        references = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            references.extend(matches)

        return list(set(references))  # Remove duplicates

    def chunk_document(self, document: Dict) -> List[Chunk]:
        """Override to add legal reference extraction"""
        chunks = super().chunk_document(document)

        # Add legal references to each chunk
        for chunk in chunks:
            references = self.extract_legal_references(chunk.content)
            chunk.metadata['legal_references'] = references

        return chunks


if __name__ == "__main__":
    # Test the chunker
    from document_loader import DocumentLoader
    from pathlib import Path

    loader = DocumentLoader()
    chunker = RegulationChunker(chunk_size=256, chunk_overlap=20)

    # Load and chunk a sample document
    sample_dir = Path(__file__).parent.parent.parent / "data" / "sample_docs"

    if sample_dir.exists():
        docs = loader.load_directory(str(sample_dir))

        for doc in docs[:1]:  # Test with first document
            print(f"\n\nProcessing: {doc['metadata']['filename']}")
            chunks = chunker.chunk_document(doc)

            print(f"Created {len(chunks)} chunks")

            # Show first 3 chunks
            for chunk in chunks[:3]:
                print(f"\n--- Chunk {chunk.chunk_id} ---")
                print(f"Section: {chunk.metadata.get('section', 'N/A')}")
                print(f"References: {chunk.metadata.get('legal_references', [])}")
                print(f"Content preview: {chunk.content[:200]}...")
