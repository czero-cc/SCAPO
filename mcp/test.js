#!/usr/bin/env node
import { spawn } from 'child_process';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

console.log('Testing MCP Server...\n');

// Simple smoke test to verify MCP server starts and responds
const mcpProcess = spawn('node', [join(__dirname, 'index.js')], {
  stdio: ['pipe', 'pipe', 'pipe']
});

let testPassed = false;

mcpProcess.stderr.on('data', (data) => {
  const message = data.toString();
  if (message.includes('SCAPO MCP Server running on stdio')) {
    console.log('✅ MCP Server started successfully');
    testPassed = true;
    
    // Send a simple request to verify it responds
    const initRequest = {
      jsonrpc: "2.0",
      method: "initialize",
      params: {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: {
          name: "test-client",
          version: "1.0.0"
        }
      },
      id: 0
    };
    mcpProcess.stdin.write(JSON.stringify(initRequest) + '\n');
  }
});

mcpProcess.stdout.on('data', (data) => {
  try {
    const response = JSON.parse(data.toString().trim());
    if (response.result && response.result.capabilities) {
      console.log('✅ MCP Server responds to initialization');
      console.log('✅ All tests passed!\n');
      mcpProcess.kill();
      process.exit(0);
    }
  } catch (e) {
    // Not JSON, ignore
  }
});

// Timeout after 5 seconds
setTimeout(() => {
  if (!testPassed) {
    console.error('❌ Test failed: Server did not start within 5 seconds');
    mcpProcess.kill();
    process.exit(1);
  }
}, 5000);

process.on('SIGINT', () => {
  mcpProcess.kill();
  process.exit(1);
});