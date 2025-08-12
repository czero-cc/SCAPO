import { readdirSync, statSync, existsSync } from 'fs';
import { join } from 'path';

export class FuzzyModelMatcher {
  constructor(modelsPath) {
    this.modelsPath = modelsPath;
    this.modelCache = null;
    this.lastCacheTime = 0;
    this.cacheTimeout = 60000; // 1 minute cache
  }

  // Build or refresh the model cache
  buildModelCache() {
    const now = Date.now();
    if (this.modelCache && (now - this.lastCacheTime) < this.cacheTimeout) {
      return this.modelCache;
    }

    const cache = new Map();
    const categories = ['text', 'image', 'video', 'audio', 'multimodal', 'code'];
    
    for (const category of categories) {
      const catPath = join(this.modelsPath, category);
      
      if (existsSync(catPath)) {
        const models = readdirSync(catPath).filter(f => {
          const modelPath = join(catPath, f);
          return statSync(modelPath).isDirectory();
        });
        
        for (const model of models) {
          // Store multiple variations for matching
          const normalizedName = this.normalizeString(model);
          
          // Add exact model name
          cache.set(model.toLowerCase(), { name: model, category, score: 1.0 });
          
          // Add normalized version
          cache.set(normalizedName, { name: model, category, score: 0.95 });
          
          // Add common variations
          const variations = this.generateVariations(model);
          for (const variation of variations) {
            if (!cache.has(variation)) {
              cache.set(variation, { name: model, category, score: 0.9 });
            }
          }
          
          // Add service-specific mappings (for services folder)
          if (category === 'video' && model.toLowerCase().includes('heygen')) {
            cache.set('heygen', { name: model, category, score: 1.0 });
          }
        }
      }
    }
    
    // Also check services folder for additional models
    const servicesPath = join(this.modelsPath, '..', 'services');
    if (existsSync(servicesPath)) {
      const serviceCategories = ['audio', 'image', 'video'];
      
      for (const category of serviceCategories) {
        const catPath = join(servicesPath, category);
        
        if (existsSync(catPath)) {
          const services = readdirSync(catPath).filter(f => {
            const servicePath = join(catPath, f);
            return statSync(servicePath).isDirectory();
          });
          
          for (const service of services) {
            const key = service.toLowerCase();
            if (!cache.has(key)) {
              cache.set(key, { name: service, category, isService: true, score: 1.0 });
            }
          }
        }
      }
    }
    
    this.modelCache = cache;
    this.lastCacheTime = now;
    return cache;
  }

  // Generate common variations of model names
  generateVariations(modelName) {
    const variations = new Set();
    const lower = modelName.toLowerCase();
    
    // Remove common suffixes/prefixes
    const cleanedVersions = [
      lower.replace(/-instruct$/i, ''),
      lower.replace(/-chat$/i, ''),
      lower.replace(/-gguf$/i, ''),
      lower.replace(/-1m$/i, ''),
      lower.replace(/^gemini-/, 'gemini'),
      lower.replace(/-cli$/, ''),
    ];
    
    // Add version-less names
    const versionLess = lower.replace(/-[\d.]+[a-z]*$/i, '');
    if (versionLess !== lower) {
      variations.add(versionLess);
    }
    
    // Add number-only versions (e.g., "qwen3" for "Qwen3-14B")
    const baseOnly = lower.match(/^[a-z]+\d*/i);
    if (baseOnly) {
      variations.add(baseOnly[0]);
    }
    
    // Add hyphenated to underscore and vice versa
    variations.add(lower.replace(/-/g, '_'));
    variations.add(lower.replace(/_/g, '-'));
    
    // Add space-separated version
    variations.add(lower.replace(/[-_]/g, ' '));
    
    // Add all cleaned versions
    cleanedVersions.forEach(v => variations.add(v));
    
    return Array.from(variations);
  }

  // Normalize string for matching
  normalizeString(str) {
    return str.toLowerCase()
      .replace(/[^a-z0-9]/g, '')
      .trim();
  }

  // Calculate similarity score between two strings
  calculateSimilarity(str1, str2) {
    const s1 = this.normalizeString(str1);
    const s2 = this.normalizeString(str2);
    
    // Exact match
    if (s1 === s2) return 1.0;
    
    // Substring match
    if (s1.includes(s2) || s2.includes(s1)) return 0.8;
    
    // Levenshtein distance
    const distance = this.levenshteinDistance(s1, s2);
    const maxLen = Math.max(s1.length, s2.length);
    const similarity = 1 - (distance / maxLen);
    
    return similarity;
  }

  // Levenshtein distance calculation
  levenshteinDistance(str1, str2) {
    const matrix = [];
    
    for (let i = 0; i <= str2.length; i++) {
      matrix[i] = [i];
    }
    
    for (let j = 0; j <= str1.length; j++) {
      matrix[0][j] = j;
    }
    
    for (let i = 1; i <= str2.length; i++) {
      for (let j = 1; j <= str1.length; j++) {
        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1, // substitution
            matrix[i][j - 1] + 1,     // insertion
            matrix[i - 1][j] + 1      // deletion
          );
        }
      }
    }
    
    return matrix[str2.length][str1.length];
  }

  // Find best matching model
  findBestMatch(query, threshold = 0.3) {
    const cache = this.buildModelCache();
    const queryLower = query.toLowerCase();
    const queryNormalized = this.normalizeString(query);
    
    // First check cache for exact or close matches
    if (cache.has(queryLower)) {
      const match = cache.get(queryLower);
      return { ...match, similarity: 1.0, matchType: 'exact' };
    }
    
    if (cache.has(queryNormalized)) {
      const match = cache.get(queryNormalized);
      return { ...match, similarity: 0.95, matchType: 'normalized' };
    }
    
    // Calculate similarity scores for all models
    const matches = [];
    const processedModels = new Set();
    
    for (const [key, value] of cache.entries()) {
      // Skip if we've already processed this actual model
      if (processedModels.has(value.name)) continue;
      processedModels.add(value.name);
      
      const similarity = this.calculateSimilarity(query, value.name);
      if (similarity >= threshold) {
        matches.push({
          ...value,
          similarity,
          matchType: 'fuzzy'
        });
      }
    }
    
    // Sort by similarity score
    matches.sort((a, b) => b.similarity - a.similarity);
    
    // Return best match or null
    return matches.length > 0 ? matches[0] : null;
  }

  // Find multiple matching models
  findMatches(query, limit = 5, threshold = 0.3) {
    const cache = this.buildModelCache();
    const queryLower = query.toLowerCase();
    
    // Calculate similarity scores for all unique models
    const matches = [];
    const processedModels = new Set();
    
    for (const [key, value] of cache.entries()) {
      // Skip if we've already processed this actual model
      if (processedModels.has(value.name)) continue;
      processedModels.add(value.name);
      
      const similarity = this.calculateSimilarity(query, value.name);
      if (similarity >= threshold) {
        matches.push({
          ...value,
          similarity,
          matchType: similarity === 1.0 ? 'exact' : similarity >= 0.8 ? 'close' : 'fuzzy'
        });
      }
    }
    
    // Sort by similarity score and return top matches
    matches.sort((a, b) => b.similarity - a.similarity);
    return matches.slice(0, limit);
  }

  // Get suggestions for typos or partial matches
  getSuggestions(query, maxSuggestions = 3) {
    const matches = this.findMatches(query, maxSuggestions, 0.2);
    return matches.map(m => ({
      model: m.name,
      category: m.category,
      confidence: Math.round(m.similarity * 100)
    }));
  }
}