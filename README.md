# Discord Bots Collection

A collection of Discord bots for server management and utility functions.

## Bots Included

- **ban-stats**: Tracks and analyzes ban statistics with charts
- **random-colors**: Manages dynamic role colors for users
- **summary**: Summarizes Discord channel conversations using AI
- **flowchart**: Posts useful flowchart links on command

## Quick Start

### 1. Setup Environment
```bash
# Clone the repository
git clone <repository-url>
cd discord-bots

# Setup Python environment and dependencies
./scripts/setup_venv.sh
```

### 2. Configure Environment Variables
Copy the `.env.example` files to `.env` in each bot directory and fill in your values:

```bash
# For each bot directory
cp ban_stats/.env.example ban_stats/.env
cp random_colors/.env.example random_colors/.env
cp summary/.env.example summary/.env
cp flowchart/.env.example flowchart/.env
```

### 3. Deploy All Bots
```bash
./scripts/deploy.sh
```

## Environment Variables

### ban-stats
- `DISCORD_TOKEN`: Your Discord bot token
- `GUILD_ID`: Your Discord server ID

### random-colors  
- `DISCORD_TOKEN`: Your Discord bot token
- `GUILD_ID`: Your Discord server ID
- `ROLE_NAME`: Name of the color role (default: "Random Colors")
- `LOG_CHANNEL_ID`: Channel ID for logging color changes

### summary
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `BOT_TOKEN`: Your Discord bot token
- `GUILD_ID`: Your Discord server ID

### flowchart
- `DISCORD_BOT_TOKEN`: Your Discord bot token

## Dependencies

All dependencies are managed through `requirements.txt` files:
- Main project: `/requirements.txt`
- Individual bots: `<bot_name>/requirements.txt`

## Process Management

Bots are managed using PM2 for production deployment:

```bash
# View status
pm2 status

# View logs
pm2 logs

# Restart all bots
pm2 restart all

# Stop all bots
pm2 stop all
```

## File Structure

```
discord-bots/
├── ban_stats/
│   ├── src/main.py
│   ├── .env.example
│   └── requirements.txt
├── random_colors/
│   ├── src/main.py
│   ├── .env.example
│   └── requirements.txt
├── summary/
│   ├── src/summarizer_bot.py
│   ├── .env.example
│   └── requirements.txt
├── flowchart/
│   ├── src/main.py
│   ├── .env.example
│   └── requirements.txt
├── scripts/
│   ├── setup_venv.sh
│   └── deploy.sh
├── logs/
├── ecosystem.config.js
└── requirements.txt
```

## Automated Deployment with GitHub Actions

This repository includes automated deployment via GitHub Actions that triggers on every push to the `main` branch.

### Setup GitHub Actions Deployment

1. **Configure SSH Access**: Follow the [SSH Setup Guide](SSH_SETUP.md) to set up SSH access to your VM.

2. **Add GitHub Secrets**: In your repository settings, add the required secrets:
   ```
   SSH_PRIVATE_KEY          # Private SSH key for VM access
   SERVER_HOST              # VM IP address or domain  
   SSH_USER                 # VM username
   PROJECT_PATH             # Full path to project on VM
   BAN_STATS_DISCORD_TOKEN  # Discord token for ban stats bot
   RANDOM_COLORS_DISCORD_TOKEN # Discord token for random colors bot
   SUMMARY_BOT_TOKEN        # Discord token for summary bot
   FLOWCHART_BOT_TOKEN      # Discord token for flowchart bot
   OPENROUTER_API_KEY       # OpenRouter API key
   GUILD_ID                 # Your Discord server ID
   RANDOM_COLORS_LOG_CHANNEL_ID # Channel ID for color logs
   ```

3. **Initial VM Setup**: Prepare your VM with the necessary dependencies:
   ```bash
   # Install Node.js and PM2
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt-get install -y nodejs
   sudo npm install -g pm2
   
   # Install Python
   sudo apt-get install -y python3 python3-venv python3-pip
   
   # Clone repository
   git clone https://github.com/YOUR_USERNAME/discord-bots.git /path/to/project
   ```

4. **Deploy**: Push to the main branch or manually trigger the workflow to deploy.

### Workflow Features

- ✅ Automated deployment on push to main branch
- ✅ Environment file creation from GitHub secrets
- ✅ Dependency installation and updates
- ✅ PM2 process management
- ✅ Deployment verification
- ✅ Manual workflow dispatch option

## Security

- All `.env` files with sensitive tokens are gitignored
- Use `.env.example` files as templates
- Never commit actual tokens or API keys
- GitHub Actions uses encrypted secrets for secure deployment
- SSH keys are dedicated for deployment use only