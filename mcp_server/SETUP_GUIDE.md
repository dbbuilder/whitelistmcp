# Claude Desktop MCP Server Setup Guide

## Quick Setup Instructions

### Step 1: Install Dependencies

Open a command prompt and navigate to the MCP server directory:

```cmd
cd D:\dev2\awswhitelist2\mcp_server
```

For Python version:
```cmd
pip install mcp boto3
```

For TypeScript version:
```cmd
npm install
npm run build
```

### Step 2: Configure Claude Desktop

1. **Find your Claude Desktop configuration file:**
   - Press `Win + R`, type `%APPDATA%\Claude` and press Enter
   - Look for `claude_desktop_config.json`
   - If it doesn't exist, create it

2. **Edit the configuration file** and add:

```json
{
  "mcpServers": {
    "aws-security-group": {
      "command": "python",
      "args": ["D:\\dev2\\awswhitelist2\\mcp_server\\server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

3. **Save the file** and **restart Claude Desktop**

### Step 3: Test the Integration

In Claude Desktop, try these commands:

1. **Test connection:**
   ```
   Can you test the AWS connection using the aws-security-group MCP server?
   ```

2. **List rules:**
   ```
   Can you list the security group rules for sg-0f0df629567eb6344 on port 8080?
   ```

3. **Add a rule:**
   ```
   Please add my IP 203.0.113.45 to security group sg-0f0df629567eb6344 
   on port 8080. Use username john_doe and resource name WebApp.
   ```

## How It Works

When you ask Claude to manage security groups:

1. Claude recognizes the request needs the MCP server
2. Claude calls the appropriate tool with parameters
3. The MCP server executes the Python script
4. Results are returned to Claude
5. Claude formats and presents the results to you

## Example Interactions

### Simple Request
```
Human: Add IP 192.168.1.100 to the dev security group for port 3000

Claude: I'll add that IP address to the security group. Let me set that up for you.

[Uses MCP server to add the rule]

Successfully added the security group rule:
- IP: 192.168.1.100/32
- Port: 3000
- Security Group: sg-0f0df629567eb6344
- Description: DevEC2 - 3000-auto-user-20250711-1500
```

### Detailed Request
```
Human: I need to whitelist these IPs for our staging environment:
- 10.0.0.50 on port 443
- 10.0.0.51 on port 443
Use the security group sg-0f0df629567eb6344 and label them as "StagingAPI"

Claude: I'll add both IP addresses to the security group for HTTPS access.

[Processes each IP address]

Successfully added 2 security group rules:
1. 10.0.0.50/32 - Port 443 - StagingAPI
2. 10.0.0.51/32 - Port 443 - StagingAPI
```

## Troubleshooting

### MCP Server Not Found
- Check the path in claude_desktop_config.json
- Ensure backslashes are escaped (\\)
- Verify Python is in your PATH

### Permission Errors
- Run Claude Desktop as administrator (once)
- Check file permissions on the scripts
- Ensure AWS credentials have proper permissions

### No Response from Server
- Check if Python/Node is installed
- Verify all dependencies are installed
- Look for errors in Claude's developer console

## Advanced Usage

### Custom Parameters
You can specify exact parameters:
```
Add this rule using the MCP server:
- Username: dev_team
- IP: 172.16.0.10
- Port: 5432
- Security Group: sg-0f0df629567eb6344
- Resource: PostgresDB
```

### Batch Operations
```
Please add these three IPs to port 8080:
- 192.168.1.10 (label: Office1)
- 192.168.1.20 (label: Office2)  
- 192.168.1.30 (label: Office3)
```

### Query Existing Rules
```
Show me all rules for port 22 in the development security group
```

## Security Notes

- The MCP server uses embedded AWS credentials
- Consider using environment variables for production
- All actions are logged with timestamps
- Rules include audit trail in descriptions

## Next Steps

1. Test with simple commands first
2. Gradually increase complexity
3. Monitor AWS console for rule changes
4. Review logs for any errors
5. Customize for your workflow