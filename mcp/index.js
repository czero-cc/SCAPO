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
                enum: ['text', 'image', 'video', 'audio', 'multimodal', 'all'],
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
    
    // Only use local files
    const practices = this.getLocalPractices(model_name, practice_type);
    
    if (practices) {
      return {
        content: [
          {
            type: 'text',
            text: practices,
          },
        ],
      };
    }
    
    return {
      content: [
        {
          type: 'text',
          text: `No practices found for model: ${model_name}\n\nTip: Run the intelligent scraper to populate model data:\npython -m src.cli scrape run --sources reddit:LocalLLaMA`,
        },
      ],
    };
  }

  getLocalPractices(modelName, practiceType) {
    // Search in local models directory
    const categories = ['text', 'image', 'video', 'audio', 'multimodal'];
    
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
    return params.map(param => {
      let text = `### ${param.name}\n`;
      if (param.default_value) text += `- Default: ${param.default_value}\n`;
      if (param.recommended_range) text += `- Recommended: ${param.recommended_range}\n`;
      if (param.description) text += `- ${param.description}\n`;
      return text;
    }).join('\n');
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
    
    // Search locally first
    const localResults = this.searchLocalModels(query, limit);
    
    if (localResults.length > 0) {
      const formatted = localResults.map(
        (r) => `- ${r.model} (${r.category})`
      ).join('\n');
      
      return {
        content: [
          {
            type: 'text',
            text: `Found ${localResults.length} models:\n\n${formatted}`,
          },
        ],
      };
    }
    
    // Try API as fallback
    try {
      const response = await fetch(
        `${API_BASE_URL}/models/search?q=${encodeURIComponent(query)}&limit=${limit}`
      );
      
      if (!response.ok) {
        throw new Error('Search failed');
      }
      
      const results = await response.json();
      
      if (results.length === 0) {
        return {
          content: [
            {
              type: 'text',
            text: `No models found matching: ${query}`,
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
      return {
        content: [
          {
            type: 'text',
            text: `No models found matching: ${query}`,
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
      ? ['text', 'image', 'video', 'audio', 'multimodal']
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
    
    // Recommendations based on use case
    const recommendations = {
      code_generation: [
        'Qwen3-Coder-Flash - Fast code completion',
        'DeepCoder-14B - Advanced code understanding',
        'Phi-4-14B - Efficient code generation',
      ],
      creative_writing: [
        'Llama-3.2-1B - Lightweight creative tasks',
        'Qwen3-32B - High-quality text generation',
        'GLM-4-32B - Multilingual creative writing',
      ],
      image_generation: [
        'Stable Diffusion XL - High-quality images',
        'Midjourney v6 - Artistic style',
        'DALL-E 3 - Photorealistic images',
      ],
      chat_conversation: [
        'Gemini - Multi-turn conversations',
        'Qwen3-14B - Efficient chat model',
        'Phi-3.1-mini - Fast responses',
      ],
    };
    
    const models = recommendations[use_case] || [];
    
    if (models.length === 0) {
      return {
        content: [
          {
            type: 'text',
            text: `No specific recommendations for use case: ${use_case}\n\nAvailable use cases: ${Object.keys(recommendations).join(', ')}`,
          },
        ],
      };
    }
    
    const result = `# Recommended Models for ${use_case.replace('_', ' ').toUpperCase()}\n\n${models.map(m => `- ${m}`).join('\n')}`;
    
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