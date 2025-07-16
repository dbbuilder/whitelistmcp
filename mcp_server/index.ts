#!/usr/bin/env node
/**
 * AWS Security Group MCP Server
 * TypeScript implementation for Model Context Protocol
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as path from 'path';

const execAsync = promisify(exec);

// Path to the Python script
const PYTHON_SCRIPT_PATH = path.join(__dirname, '..', 'simple_test', 'add_sg_rule_json.py');

interface SecurityGroupRule {
  UserName: string;
  UserIP: string;
  Port: string;
  SecurityGroupID: string;
  ResourceName: string;
}

interface ExecutionResult {
  success: boolean;
  message?: string;
  error?: string;
  output?: string;
}

class AWSSecurityGroupServer {
  private server: Server;

  constructor() {
    this.server = new Server(
      {
        name: 'aws-security-group-mcp',
        version: '1.0.0',
      },
      {
        capabilities: {
          resources: {},
          tools: {},
        },
      }
    );

    this.setupHandlers();
  }

  private setupHandlers(): void {
    // Handle resource listing
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => ({
      resources: [
        {
          uri: 'aws://security-group/config',
          name: 'AWS Security Group Configuration',
          description: 'Configuration for AWS Security Group management',
          mimeType: 'application/json',
        },
      ],
    }));

    // Handle tool listing
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'add_security_group_rule',
          description: 'Add an IP address to an AWS Security Group',
          inputSchema: {
            type: 'object',
            properties: {
              UserName: {
                type: 'string',
                description: 'Username for the rule description',
              },
              UserIP: {
                type: 'string',
                description: 'IP address to whitelist (e.g., 1.1.1.1)',
              },
              Port: {
                type: 'string',
                description: 'Port number to allow access (e.g., 8080)',
              },
              SecurityGroupID: {
                type: 'string',
                description: 'AWS Security Group ID (e.g., sg-0f0df629567eb6344)',
              },
              ResourceName: {
                type: 'string',
                description: 'Resource name for the description (e.g., DevEC2)',
              },
            },
            required: ['UserName', 'UserIP', 'Port', 'SecurityGroupID', 'ResourceName'],
          },
        },
        {
          name: 'validate_rule_parameters',
          description: 'Validate security group rule parameters',
          inputSchema: {
            type: 'object',
            properties: {
              UserIP: {
                type: 'string',
                description: 'IP address to validate',
              },
              Port: {
                type: 'string',
                description: 'Port number to validate',
              },
            },
            required: ['UserIP', 'Port'],
          },
        },
      ],
    }));

    // Handle tool execution
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      if (request.params.name === 'add_security_group_rule') {
        return await this.handleAddSecurityGroupRule(request.params.arguments as SecurityGroupRule);
      } else if (request.params.name === 'validate_rule_parameters') {
        return await this.handleValidateParameters(request.params.arguments as any);
      } else {
        throw new McpError(
          ErrorCode.MethodNotFound,
          `Unknown tool: ${request.params.name}`
        );
      }
    });
  }

  private async handleAddSecurityGroupRule(rule: SecurityGroupRule): Promise<any> {
    try {
      // Validate input parameters
      const validation = this.validateRule(rule);
      if (!validation.valid) {
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                success: false,
                error: validation.error,
              }, null, 2),
            },
          ],
        };
      }

      // Prepare JSON for Python script
      const jsonConfig = JSON.stringify(rule);
      
      // Execute Python script
      const result = await this.executePythonScript(jsonConfig);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2),
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error instanceof Error ? error.message : 'Unknown error',
            }, null, 2),
          },
        ],
      };
    }
  }

  private async handleValidateParameters(params: { UserIP: string; Port: string }): Promise<any> {
    const errors: string[] = [];

    // Validate IP address
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!ipRegex.test(params.UserIP)) {
      errors.push('Invalid IP address format');
    } else {
      const octets = params.UserIP.split('.').map(Number);
      if (octets.some(octet => octet < 0 || octet > 255)) {
        errors.push('IP address octets must be between 0 and 255');
      }
    }

    // Validate port
    const port = parseInt(params.Port);
    if (isNaN(port) || port < 1 || port > 65535) {
      errors.push('Port must be a number between 1 and 65535');
    }

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            valid: errors.length === 0,
            errors: errors.length > 0 ? errors : undefined,
            message: errors.length === 0 ? 'Parameters are valid' : 'Validation failed',
          }, null, 2),
        },
      ],
    };
  }

  private validateRule(rule: SecurityGroupRule): { valid: boolean; error?: string } {
    // Validate required fields
    const requiredFields = ['UserName', 'UserIP', 'Port', 'SecurityGroupID', 'ResourceName'];
    for (const field of requiredFields) {
      if (!rule[field as keyof SecurityGroupRule]) {
        return { valid: false, error: `Missing required field: ${field}` };
      }
    }

    // Validate IP address format
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!ipRegex.test(rule.UserIP)) {
      return { valid: false, error: 'Invalid IP address format' };
    }

    // Validate port number
    const port = parseInt(rule.Port);
    if (isNaN(port) || port < 1 || port > 65535) {
      return { valid: false, error: 'Port must be between 1 and 65535' };
    }

    // Validate security group ID format
    if (!rule.SecurityGroupID.startsWith('sg-')) {
      return { valid: false, error: 'Security Group ID must start with "sg-"' };
    }

    return { valid: true };
  }

  private async executePythonScript(jsonConfig: string): Promise<ExecutionResult> {
    try {
      const command = `python "${PYTHON_SCRIPT_PATH}" '${jsonConfig}'`;
      const { stdout, stderr } = await execAsync(command);

      if (stderr && !stdout) {
        return {
          success: false,
          error: stderr,
        };
      }

      // Parse the output to determine success
      const output = stdout.trim();
      const success = output.includes('SUCCESS') && !output.includes('FAILED');

      return {
        success,
        message: success ? 'Security group rule added successfully' : 'Failed to add security group rule',
        output,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error executing Python script',
      };
    }
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('AWS Security Group MCP server running on stdio');
  }
}

// Main entry point
const server = new AWSSecurityGroupServer();
server.run().catch(console.error);
