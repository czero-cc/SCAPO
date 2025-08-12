#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import fetch from 'node-fetch';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { readFileSync, existsSync, readdirSync, statSync } from 'fs';
import { FuzzyModelMatcher } from './fuzzyMatcher.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Server configuration
const API_BASE_URL = process.env.SCAPO_API_URL || 'http://localhost:8000/api/v1';
const LOCAL_MODELS_PATH = process.env.SCAPO_MODELS_PATH || join(dirname(__dirname), 'models');

class SCAPOServer {
  constructor() {
    this.server = new Server(
      {
        name: 'scapo-mcp',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.fuzzyMatcher = new FuzzyModelMatcher(LOCAL_MODELS_PATH);
    this.setupHandlers();
  }

  setupHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'get_best_practices',
          description: 'Get AI/ML best practices for a specific model',
          inputSchema: {
            type: 'object',
            properties: {
              model_name: {
                type: 'string',
                description: 'Model name (e.g., gpt-4, claude-3, stable-diffusion)',
              },
              practice_type: {
                type: 'string',
                enum: ['all', 'prompting', 'parameters', 'pitfalls'],
                description: 'Type of practices to retrieve',
                default: 'all',
              },
            },
            required: ['model_name'],
          },
        },
        {
          name: 'search_models',
          description: 'Search for models by keyword',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'Search query',
              },
              limit: {
                type: 'number',
                description: 'Maximum results',
                default: 10,
              },
            },
            required: ['query'],
          },
        },
        {
          name: 'list_models',
          description: 'List all available models by category',
          inputSchema: {
            type: 'object',
            properties: {
              category: {
                type: 'string',
                enum: ['text', 'image', 'video', 'audio', 'multimodal', 'code', 'all'],
                description: 'Model category',
                default: 'all',
              },
            },
          },
        },
        {
          name: 'get_recommended_models',
          description: 'Get recommended models for a specific use case',
          inputSchema: {
            type: 'object',
            properties: {
              use_case: {
                type: 'string',
                description: 'Use case (e.g., code_generation, creative_writing, image_generation)',
              },
            },
            required: ['use_case'],
          },
        },
      ],
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'get_best_practices':
            return await this.getBestPractices(args);
          
          case 'search_models':
            return await this.searchModels(args);
          
          case 'list_models':
            return await this.listModels(args);
          
          case 'get_recommended_models':
            return await this.getRecommendedModels(args);
          
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error.message}`,
            },
          ],
        };
      }
    });
  }

  async getBestPractices(args) {
    const { model_name, practice_type = 'all' } = args;
    
    // Try fuzzy matching first
    const match = this.fuzzyMatcher.findBestMatch(model_name);
    
    if (match) {
      // Check if it's a service (e.g., heygen in services folder)
      if (match.isService) {
        const servicePath = join(dirname(LOCAL_MODELS_PATH), 'services', match.category, match.name);
        const serviceInfo = this.getServiceInfo(servicePath, match.name);
        if (serviceInfo) {
          return {
            content: [
              {
                type: 'text',
                text: serviceInfo,
              },
            ],
          };
        }
      }
      
      // Use the matched model name for local practices
      const practices = this.getLocalPractices(match.name, practice_type);
      
      if (practices) {
        let resultText = practices;
        
        // Add match information if it wasn't exact
        if (match.matchType !== 'exact') {
          resultText = `*Note: Showing results for "${match.name}" (${match.matchType} match for "${model_name}")*\n\n${practices}`;
        }
        
        return {
          content: [
            {
              type: 'text',
              text: resultText,
            },
          ],
        };
      }
    }
    
    // Try to provide suggestions if no match found
    const suggestions = this.fuzzyMatcher.getSuggestions(model_name);
    
    if (suggestions.length > 0) {
      const suggestionText = suggestions.map(s => `- ${s.model} (${s.category}) - ${s.confidence}% match`).join('\n');
      return {
        content: [
          {
            type: 'text',
            text: `No exact match found for "${model_name}".\n\nDid you mean one of these?\n${suggestionText}\n\nIf you're looking for a different model, it may not be registered yet.\nPlease contribute or open an issue at: https://github.com/czero-cc/SCAPO/`,
          },
        ],
      };
    }
    
    return {
      content: [
        {
          type: 'text',
          text: `Model "${model_name}" is not yet registered in SCAPO.\n\nThis repository is continuously evolving. You can:\n1. Open an issue to request this model: https://github.com/czero-cc/SCAPO/issues\n2. Contribute best practices for this model: https://github.com/czero-cc/SCAPO/\n\nCurrently registered models can be listed using the 'list_models' tool.`,
        },
      ],
    };
  }

  getServiceInfo(servicePath, serviceName) {
    // For services like HeyGen, provide available information
    const info = [];
    info.push(`# ${serviceName} Service Information\n`);
    
    // Check for README or documentation
    const readmePath = join(servicePath, 'README.md');
    if (existsSync(readmePath)) {
      info.push(readFileSync(readmePath, 'utf-8'));
    }
    
    // Check for configuration files
    const configPath = join(servicePath, 'config.json');
    if (existsSync(configPath)) {
      const config = JSON.parse(readFileSync(configPath, 'utf-8'));
      info.push(`## Configuration\n\n${JSON.stringify(config, null, 2)}`);
    }
    
    // List available files in the service directory
    if (existsSync(servicePath)) {
      const files = readdirSync(servicePath);
      if (files.length > 0) {
        info.push(`## Available Resources\n\n${files.map(f => `- ${f}`).join('\n')}`);
      }
    }
    
    return info.length > 1 ? info.join('\n\n') : null;
  }

  getLocalPractices(modelName, practiceType) {
    // Search in local models directory
    const categories = ['text', 'image', 'video', 'audio', 'multimodal', 'code'];
    
    for (const category of categories) {
      const modelPath = join(LOCAL_MODELS_PATH, category, modelName);
      
      if (existsSync(modelPath)) {
        const practices = [];
        
        if (practiceType === 'all' || practiceType === 'prompting') {
          const promptingPath = join(modelPath, 'prompting.md');
          if (existsSync(promptingPath)) {
            practices.push(`## Prompting Guide\n\n${readFileSync(promptingPath, 'utf-8')}`);
          }
        }
        
        if (practiceType === 'all' || practiceType === 'parameters') {
          const paramsPath = join(modelPath, 'parameters.json');
          if (existsSync(paramsPath)) {
            const params = JSON.parse(readFileSync(paramsPath, 'utf-8'));
            practices.push(`## Parameters\n\n${this.formatParameters(params)}`);
          }
        }
        
        if (practiceType === 'all' || practiceType === 'pitfalls') {
          const pitfallsPath = join(modelPath, 'pitfalls.md');
          if (existsSync(pitfallsPath)) {
            practices.push(`## Common Pitfalls\n\n${readFileSync(pitfallsPath, 'utf-8')}`);
          }
        }
        
        if (practices.length > 0) {
          return `# ${modelName} Best Practices\n\n${practices.join('\n\n')}`;
        }
      }
    }
    
    return null;
  }

  formatParameters(params) {
    // Handle both array format and object format
    if (Array.isArray(params)) {
      return params.map(param => {
        let text = `### ${param.name}\n`;
        if (param.default_value) text += `- Default: ${param.default_value}\n`;
        if (param.recommended_range) text += `- Recommended: ${param.recommended_range}\n`;
        if (param.description) text += `- ${param.description}\n`;
        return text;
      }).join('\n');
    } else if (typeof params === 'object') {
      // Handle the current format in parameters.json files
      let text = '';
      if (params.recommended_settings) {
        text += '### Recommended Settings\n';
        Object.values(params.recommended_settings).forEach(setting => {
          if (setting.description) text += `- ${setting.description}\n`;
        });
      }
      if (params.cost_optimization) {
        text += '\n### Cost Optimization\n';
        if (params.cost_optimization.pricing) {
          text += `- Pricing: ${params.cost_optimization.pricing}\n`;
        }
        Object.entries(params.cost_optimization).forEach(([key, value]) => {
          if (key.startsWith('tip_')) {
            text += `- ${value}\n`;
          }
        });
      }
      return text;
    }
    return 'No parameters available';
  }

  formatPractices(data, modelName) {
    let result = `# ${modelName} Best Practices\n\n`;
    
    if (data.prompt_structure) {
      result += `## Prompting Guide\n\n${data.prompt_structure}\n\n`;
    }
    
    if (data.parameters && data.parameters.length > 0) {
      result += `## Parameters\n\n${this.formatParameters(data.parameters)}\n\n`;
    }
    
    if (data.pitfalls && data.pitfalls.length > 0) {
      result += `## Common Pitfalls\n\n`;
      data.pitfalls.forEach(pitfall => {
        result += `### ${pitfall.title}\n${pitfall.description}\n`;
        if (pitfall.solution) {
          result += `**Solution:** ${pitfall.solution}\n`;
        }
        result += '\n';
      });
    }
    
    return result;
  }

  async searchModels(args) {
    const { query, limit = 10 } = args;
    
    // Use fuzzy matcher for search
    const matches = this.fuzzyMatcher.findMatches(query, limit);
    
    if (matches.length > 0) {
      const formatted = matches.map(m => {
        const confidence = Math.round(m.similarity * 100);
        return `- ${m.name} (${m.category}) - ${confidence}% match [${m.matchType}]`;
      }).join('\n');
      
      return {
        content: [
          {
            type: 'text',
            text: `Found ${matches.length} models matching "${query}":\n\n${formatted}`,
          },
        ],
      };
    }
    
    // Try API as fallback if no local matches
    try {
      const response = await fetch(
        `${API_BASE_URL}/models/search?q=${encodeURIComponent(query)}&limit=${limit}`
      );
      
      if (!response.ok) {
        throw new Error('Search failed');
      }
      
      const results = await response.json();
      
      if (results.length === 0) {
        // Provide suggestions from actual registered models
        const suggestions = this.fuzzyMatcher.getSuggestions(query, 5);
        if (suggestions.length > 0) {
          const suggestionText = suggestions.map(s => `- ${s.model} (${s.category})`).join('\n');
          return {
            content: [
              {
                type: 'text',
                text: `No models found matching: ${query}\n\nSimilar registered models:\n${suggestionText}\n\nIf you're looking for a different model, it may not be registered yet.\nContribute at: https://github.com/czero-cc/SCAPO/`,
              },
            ],
          };
        }
        
        return {
          content: [
            {
              type: 'text',
              text: `No models found matching: ${query}\n\nThis model may not be registered yet in SCAPO.\nYou can:\n1. Check available models with 'list_models' tool\n2. Request this model: https://github.com/czero-cc/SCAPO/issues\n3. Contribute: https://github.com/czero-cc/SCAPO/`,
            },
          ],
        };
      }
      
      const formatted = results.map(
        (r) => `- ${r.model_id} (${r.category}) - Match: ${r.match_type}`
      ).join('\n');
      
      return {
        content: [
          {
            type: 'text',
            text: `Found ${results.length} models:\n\n${formatted}`,
          },
        ],
      };
    } catch (error) {
      // Provide suggestions from actual registered models on error
      const suggestions = this.fuzzyMatcher.getSuggestions(query, 3);
      if (suggestions.length > 0) {
        const suggestionText = suggestions.map(s => `- ${s.model} (${s.category})`).join('\n');
        return {
          content: [
            {
              type: 'text',
              text: `Search failed for: ${query}\n\nRegistered models similar to your search:\n${suggestionText}\n\nFor other models, visit: https://github.com/czero-cc/SCAPO/`,
            },
          ],
        };
      }
      
      return {
        content: [
          {
            type: 'text',
            text: `No models found matching: ${query}\n\nSCApo repository is continuously evolving.\nContribute or request models at: https://github.com/czero-cc/SCAPO/`,
          },
        ],
      };
    }
  }
  
  searchLocalModels(query, limit) {
    const results = [];
    const searchTerm = query.toLowerCase();
    const categories = ['text', 'image', 'video', 'audio', 'multimodal'];
    
    for (const category of categories) {
      const catPath = join(LOCAL_MODELS_PATH, category);
      
      if (existsSync(catPath)) {
        const models = readdirSync(catPath).filter(f => {
          const modelPath = join(catPath, f);
          return statSync(modelPath).isDirectory() && f.toLowerCase().includes(searchTerm);
        });
        
        for (const model of models) {
          results.push({ model, category });
          if (results.length >= limit) return results;
        }
      }
    }
    
    return results;
  }

  async listModels(args) {
    const { category = 'all' } = args;
    
    // Always use local directory listing
    return this.listLocalModels(category);
  }

  listLocalModels(category) {
    let result = '# Available Models (Local)\n\n';
    
    const categories = category === 'all'
      ? ['text', 'image', 'video', 'audio', 'multimodal', 'code']
      : [category];
    
    for (const cat of categories) {
      const catPath = join(LOCAL_MODELS_PATH, cat);
      
      if (existsSync(catPath)) {
        const models = readdirSync(catPath).filter(f => {
          const modelPath = join(catPath, f);
          return statSync(modelPath).isDirectory();
        });
        
        if (models.length > 0) {
          result += `## ${cat.toUpperCase()}\n`;
          models.forEach(model => {
            result += `- ${model}\n`;
          });
          result += '\n';
        }
      }
    }
    
    return {
      content: [
        {
          type: 'text',
          text: result,
        },
      ],
    };
  }

  async getRecommendedModels(args) {
    const { use_case } = args;
    
    // Map use cases to model categories ONLY - no hardcoded keywords!
    const useCaseMapping = {
      code_generation: ['code'],
      creative_writing: ['text'],
      image_generation: ['image'],
      video_generation: ['video'],
      audio_generation: ['audio'],
      chat_conversation: ['text', 'multimodal'],
      multimodal_tasks: ['multimodal'],
    };
    
    const relevantCategories = useCaseMapping[use_case];
    
    if (!relevantCategories) {
      return {
        content: [
          {
            type: 'text',
            text: `Use case "${use_case}" is not recognized.\n\nSupported use cases: ${Object.keys(useCaseMapping).join(', ')}\n\nFor model recommendations, please check our repository: https://github.com/czero-cc/SCAPO/`,
          },
        ],
      };
    }
    
    // Get actual models from the file system - no keyword matching!
    const relevantModels = [];
    
    for (const category of relevantCategories) {
      const catPath = join(LOCAL_MODELS_PATH, category);
      
      if (existsSync(catPath)) {
        const models = readdirSync(catPath).filter(f => {
          const modelPath = join(catPath, f);
          return statSync(modelPath).isDirectory();
        });
        
        for (const model of models) {
          relevantModels.push(`${model} (${category})`);
        }
      }
    }
    
    if (relevantModels.length === 0) {
      return {
        content: [
          {
            type: 'text',
            text: `No registered models found for ${use_case.replace('_', ' ')}.\n\nSCApo is continuously evolving. To add models for this use case:\n- Open an issue: https://github.com/czero-cc/SCAPO/issues\n- Contribute: https://github.com/czero-cc/SCAPO/\n\nUse 'list_models' to see currently available models.`,
          },
        ],
      };
    }
    
    const result = `# Available Models for ${use_case.replace('_', ' ').toUpperCase()}\n\n${relevantModels.map(m => `- ${m}`).join('\n')}\n\nNote: This list only includes currently registered models in SCAPO.\nFor more models, contribute at: https://github.com/czero-cc/SCAPO/`;
    
    return {
      content: [
        {
          type: 'text',
          text: result,
        },
      ],
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('SCAPO MCP Server running on stdio');
  }
}

// Run the server
const server = new SCAPOServer();
server.run().catch(console.error);