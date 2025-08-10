"""Enhanced content processing with intelligent chunking and multi-pass extraction."""

import re
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

from src.core.logging import get_logger
from src.core.config import settings

logger = get_logger(__name__)


@dataclass
class ContentChunk:
    """Represents a chunk of content with metadata."""
    text: str
    start_pos: int
    end_pos: int
    chunk_index: int
    total_chunks: int
    overlap_with_previous: int = 0
    overlap_with_next: int = 0
    section_headers: List[str] = field(default_factory=list)
    
    @property
    def chunk_id(self) -> str:
        """Generate unique ID for this chunk."""
        return hashlib.md5(f"{self.start_pos}:{self.end_pos}".encode()).hexdigest()[:8]


class ContentChunker:
    """Intelligent content chunking with context preservation."""
    
    def __init__(self, 
                 chunk_size: int = 8000,
                 overlap_size: int = 500,
                 min_chunk_size: int = 1000):
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size
        
    def chunk_with_overlap(self, content: str) -> List[ContentChunk]:
        """Create overlapping chunks to preserve context across boundaries."""
        if len(content) <= self.chunk_size:
            return [ContentChunk(
                text=content,
                start_pos=0,
                end_pos=len(content),
                chunk_index=0,
                total_chunks=1
            )]
        
        chunks = []
        content_length = len(content)
        step_size = self.chunk_size - self.overlap_size
        
        # Calculate total chunks for progress tracking
        total_chunks = ((content_length - self.chunk_size) // step_size) + 1
        if (content_length - self.chunk_size) % step_size > 0:
            total_chunks += 1
            
        for i, start in enumerate(range(0, content_length, step_size)):
            end = min(start + self.chunk_size, content_length)
            
            # Don't create tiny final chunks
            if end - start < self.min_chunk_size and i > 0:
                # Extend previous chunk instead
                chunks[-1].text = content[chunks[-1].start_pos:end]
                chunks[-1].end_pos = end
                break
                
            chunk = ContentChunk(
                text=content[start:end],
                start_pos=start,
                end_pos=end,
                chunk_index=i,
                total_chunks=total_chunks,
                overlap_with_previous=self.overlap_size if i > 0 else 0,
                overlap_with_next=self.overlap_size if end < content_length else 0
            )
            
            # Extract section headers if present
            chunk.section_headers = self._extract_headers(chunk.text)
            chunks.append(chunk)
            
        return chunks
    
    def chunk_by_sections(self, content: str) -> List[ContentChunk]:
        """Split content by logical sections (paragraphs, headers, etc.)."""
        # Detect markdown headers
        header_pattern = r'^#{1,6}\s+(.+)$'
        
        # Split by double newlines (paragraphs) or headers
        sections = re.split(r'\n\n+|(?=^#{1,6}\s+)', content, flags=re.MULTILINE)
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_index = 0
        start_pos = 0
        
        for section in sections:
            section_size = len(section)
            
            # If adding this section would exceed chunk size, save current chunk
            if current_size + section_size > self.chunk_size and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(ContentChunk(
                    text=chunk_text,
                    start_pos=start_pos,
                    end_pos=start_pos + len(chunk_text),
                    chunk_index=chunk_index,
                    total_chunks=0,  # Will be updated after processing all
                    section_headers=self._extract_headers(chunk_text)
                ))
                chunk_index += 1
                start_pos += len(chunk_text) + 2  # Account for separator
                current_chunk = []
                current_size = 0
            
            current_chunk.append(section)
            current_size += section_size + 2  # Account for separator
        
        # Add remaining content
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(ContentChunk(
                text=chunk_text,
                start_pos=start_pos,
                end_pos=start_pos + len(chunk_text),
                chunk_index=chunk_index,
                total_chunks=0,
                section_headers=self._extract_headers(chunk_text)
            ))
        
        # Update total chunks count
        for chunk in chunks:
            chunk.total_chunks = len(chunks)
            
        return chunks
    
    def chunk_by_semantic_boundaries(self, content: str) -> List[ContentChunk]:
        """Advanced chunking that respects semantic boundaries."""
        # Look for natural boundaries
        boundaries = [
            r'\n---+\n',  # Markdown horizontal rules
            r'\n\n#{1,6}\s+',  # Markdown headers
            r'\n\n(?:```|~~~)',  # Code blocks
            r'\n\n(?:\d+\.|\*|-)\s+',  # Lists
            r'\n\n\w',  # Paragraph starts
        ]
        
        # Create a combined pattern
        boundary_pattern = '|'.join(f'({pattern})' for pattern in boundaries)
        
        # Find all boundary positions
        boundary_positions = [(m.start(), m.end()) for m in re.finditer(boundary_pattern, content, re.MULTILINE)]
        
        # If no boundaries found, fall back to overlap chunking
        if not boundary_positions:
            return self.chunk_with_overlap(content)
        
        chunks = []
        current_start = 0
        current_text = []
        chunk_index = 0
        
        for boundary_start, boundary_end in boundary_positions:
            segment = content[current_start:boundary_start]
            
            # Check if adding this segment would exceed chunk size
            current_size = sum(len(t) for t in current_text)
            if current_size + len(segment) > self.chunk_size and current_text:
                # Save current chunk
                chunk_text = ''.join(current_text)
                chunks.append(ContentChunk(
                    text=chunk_text,
                    start_pos=current_start - current_size,
                    end_pos=current_start,
                    chunk_index=chunk_index,
                    total_chunks=0,
                    section_headers=self._extract_headers(chunk_text)
                ))
                chunk_index += 1
                current_text = []
            
            current_text.append(segment)
            current_text.append(content[boundary_start:boundary_end])
            current_start = boundary_end
        
        # Add remaining content
        if current_start < len(content):
            current_text.append(content[current_start:])
        
        if current_text:
            chunk_text = ''.join(current_text)
            chunks.append(ContentChunk(
                text=chunk_text,
                start_pos=len(content) - len(chunk_text),
                end_pos=len(content),
                chunk_index=chunk_index,
                total_chunks=0,
                section_headers=self._extract_headers(chunk_text)
            ))
        
        # Update total chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)
            
        return chunks
    
    def _extract_headers(self, text: str) -> List[str]:
        """Extract markdown headers from text."""
        headers = re.findall(r'^#{1,6}\s+(.+)$', text, re.MULTILINE)
        return headers[:5]  # Limit to first 5 headers


class MultiPassProcessor:
    """Process content in multiple passes for comprehensive extraction."""
    
    def __init__(self, llm_processor):
        self.llm_processor = llm_processor
        self.chunker = ContentChunker()
        
    async def process_hierarchical(self, content: str, source_type: str) -> Dict[str, Any]:
        """
        Multi-pass processing:
        1st pass: Extract high-level entities and themes
        2nd pass: Deep dive into specific practices per entity
        3rd pass: Cross-reference and validate
        """
        results = {
            'entities': [],
            'practices': [],
            'parameters': {},
            'themes': set(),
            'confidence_scores': {},
            'processing_metadata': {
                'content_length': len(content),
                'chunks_processed': 0,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Chunk the content intelligently
        chunks = self.chunker.chunk_by_semantic_boundaries(content)
        results['processing_metadata']['total_chunks'] = len(chunks)
        
        logger.info(f"Processing {len(chunks)} chunks for {source_type} content")
        
        # Pass 1: Entity extraction from each chunk
        chunk_entities = []
        for chunk in chunks:
            entities = await self._extract_entities(chunk, source_type)
            chunk_entities.append(entities)
            results['processing_metadata']['chunks_processed'] += 1
        
        # Merge and deduplicate entities
        results['entities'] = self._merge_entities(chunk_entities)
        
        # Pass 2: Extract practices for each identified entity
        for entity in results['entities']:
            # Process relevant chunks for this entity
            relevant_chunks = self._find_relevant_chunks(chunks, entity)
            for chunk in relevant_chunks:
                practices = await self._extract_practices_for_entity(chunk, entity, source_type)
                results['practices'].extend(practices)
        
        # Pass 3: Validate and cross-reference
        results['practices'] = await self._validate_practices(results['practices'], content)
        
        # Extract themes
        results['themes'] = self._extract_themes(results['practices'])
        
        # Calculate confidence scores
        results['confidence_scores'] = self._calculate_confidence(results)
        
        return results
    
    async def _extract_entities(self, chunk: ContentChunk, source_type: str) -> Dict[str, Any]:
        """Extract entities from a chunk."""
        prompt = f"""Analyze this {source_type} content chunk ({chunk.chunk_index + 1}/{chunk.total_chunks}) and extract AI/ML entities.

Content:
{chunk.text}

Extract:
1. AI models/services mentioned (be specific about versions)
2. Techniques and methods discussed
3. Parameters and configurations
4. Tools and platforms referenced

Return as JSON:
{{
    "models": ["model1", "model2"],
    "services": ["service1", "service2"],
    "techniques": ["technique1"],
    "parameters": {{"param": "value"}},
    "tools": ["tool1"],
    "platforms": ["platform1"]
}}"""
        
        response = await self.llm_processor.process_raw_prompt(prompt)
        try:
            return json.loads(response)
        except:
            return {"models": [], "services": [], "techniques": [], "parameters": {}, "tools": [], "platforms": []}
    
    async def _extract_practices_for_entity(self, chunk: ContentChunk, entity: str, source_type: str) -> List[Dict]:
        """Extract practices specific to an entity."""
        prompt = f"""Extract SPECIFIC best practices for {entity} from this content.

Content:
{chunk.text}

Focus on {entity} and extract:
1. Prompting techniques
2. Parameter recommendations
3. Common pitfalls
4. Tips and tricks
5. Example usage patterns

Return as JSON array of practices:
[
    {{
        "entity": "{entity}",
        "type": "prompting|parameter|pitfall|tip",
        "content": "specific practice",
        "confidence": 0.0-1.0,
        "example": "optional example"
    }}
]"""
        
        response = await self.llm_processor.process_raw_prompt(prompt)
        try:
            practices = json.loads(response)
            return practices if isinstance(practices, list) else []
        except:
            return []
    
    async def _validate_practices(self, practices: List[Dict], full_content: str) -> List[Dict]:
        """Validate and deduplicate practices."""
        # Remove duplicates based on content similarity
        unique_practices = []
        seen_contents = set()
        
        for practice in practices:
            content_hash = hashlib.md5(practice.get('content', '').encode()).hexdigest()
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_practices.append(practice)
        
        # Could add additional validation here
        return unique_practices
    
    def _merge_entities(self, chunk_entities: List[Dict]) -> List[str]:
        """Merge and deduplicate entities from all chunks."""
        all_entities = set()
        
        for entities in chunk_entities:
            all_entities.update(entities.get('models', []))
            all_entities.update(entities.get('services', []))
            all_entities.update(entities.get('tools', []))
            all_entities.update(entities.get('platforms', []))
        
        return list(all_entities)
    
    def _find_relevant_chunks(self, chunks: List[ContentChunk], entity: str) -> List[ContentChunk]:
        """Find chunks that mention a specific entity."""
        relevant = []
        entity_lower = entity.lower()
        
        for chunk in chunks:
            if entity_lower in chunk.text.lower():
                relevant.append(chunk)
        
        return relevant
    
    def _extract_themes(self, practices: List[Dict]) -> set:
        """Extract common themes from practices."""
        themes = set()
        for practice in practices:
            practice_type = practice.get('type', '')
            if practice_type:
                themes.add(practice_type)
        return themes
    
    def _calculate_confidence(self, results: Dict) -> Dict[str, float]:
        """Calculate confidence scores for the extraction."""
        scores = {}
        
        # Overall confidence based on number of practices found
        practice_count = len(results['practices'])
        scores['overall'] = min(1.0, practice_count / 10)  # Normalize to 0-1
        
        # Per-entity confidence
        entity_practices = {}
        for practice in results['practices']:
            entity = practice.get('entity', 'unknown')
            if entity not in entity_practices:
                entity_practices[entity] = []
            entity_practices[entity].append(practice.get('confidence', 0.5))
        
        for entity, confidences in entity_practices.items():
            scores[entity] = sum(confidences) / len(confidences) if confidences else 0.0
        
        return scores


class QualityScorer:
    """Score and rank practices based on multiple quality factors."""
    
    def __init__(self):
        self.source_weights = {
            'official_docs': 1.0,
            'github': 0.9,
            'reddit': 0.7,
            'discord': 0.6,
            'forum': 0.7,
            'blog': 0.5
        }
    
    def score_practice(self, practice: Dict, metadata: Dict) -> float:
        """Calculate quality score for a practice."""
        factors = {
            'source_authority': self._get_source_score(metadata.get('source', '')),
            'community_validation': self._get_community_score(metadata),
            'recency': self._calculate_recency_score(metadata.get('date')),
            'specificity': self._measure_specificity(practice.get('content', '')),
            'actionability': self._measure_actionability(practice.get('content', '')),
            'completeness': self._measure_completeness(practice)
        }
        
        weights = {
            'source_authority': 0.25,
            'community_validation': 0.20,
            'recency': 0.15,
            'specificity': 0.20,
            'actionability': 0.15,
            'completeness': 0.05
        }
        
        return sum(factors[k] * weights[k] for k in factors)
    
    def _get_source_score(self, source: str) -> float:
        """Get authority score for source."""
        source_lower = source.lower()
        for key, weight in self.source_weights.items():
            if key in source_lower:
                return weight
        return 0.5
    
    def _get_community_score(self, metadata: Dict) -> float:
        """Calculate community validation score."""
        upvotes = metadata.get('upvotes', 0)
        comments = metadata.get('comments', 0)
        
        # Normalize to 0-1 scale
        upvote_score = min(1.0, upvotes / 100)
        comment_score = min(1.0, comments / 50)
        
        return (upvote_score * 0.7 + comment_score * 0.3)
    
    def _calculate_recency_score(self, date_str: Optional[str]) -> float:
        """Calculate recency score based on date."""
        if not date_str:
            return 0.5
        
        try:
            date = datetime.fromisoformat(date_str)
            days_old = (datetime.now() - date).days
            
            if days_old < 7:
                return 1.0
            elif days_old < 30:
                return 0.8
            elif days_old < 90:
                return 0.6
            elif days_old < 180:
                return 0.4
            else:
                return 0.2
        except:
            return 0.5
    
    def _measure_specificity(self, content: str) -> float:
        """Measure how specific the practice is."""
        specificity_indicators = [
            r'\d+',  # Contains numbers
            r'`[^`]+`',  # Contains code
            r'"[^"]+"',  # Contains quoted text
            r'parameter|config|setting',  # Configuration terms
            r'version|v\d+',  # Version information
        ]
        
        score = 0.0
        for pattern in specificity_indicators:
            if re.search(pattern, content, re.IGNORECASE):
                score += 0.2
        
        return min(1.0, score)
    
    def _measure_actionability(self, content: str) -> float:
        """Measure how actionable the practice is."""
        action_words = [
            'use', 'set', 'configure', 'enable', 'disable',
            'add', 'remove', 'modify', 'change', 'update',
            'should', 'must', 'need', 'require', 'recommend'
        ]
        
        content_lower = content.lower()
        matches = sum(1 for word in action_words if word in content_lower)
        
        return min(1.0, matches / 3)  # Normalize
    
    def _measure_completeness(self, practice: Dict) -> float:
        """Measure how complete the practice information is."""
        fields = ['entity', 'type', 'content', 'example', 'confidence']
        present = sum(1 for field in fields if practice.get(field))
        
        return present / len(fields)