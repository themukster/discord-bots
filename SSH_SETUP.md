# SSH Setup Guide for GitHub Actions Deployment

This guide explains how to set up SSH access for automated deployment to your VM.

## 1. Generate SSH Key Pair

On your local machine:

```bash
# Generate a new SSH key pair specifically for GitHub Actions
ssh-keygen -t ed25519 -f ~/.ssh/github_actions_deploy -N ""

# This creates:
# ~/.ssh/github_actions_deploy (private key)
# ~/.ssh/github_actions_deploy.pub (public key)
```

## 2. Add Public Key to VM

Copy the public key to your VM:

```bash
# Copy public key content
cat ~/.ssh/github_actions_deploy.pub

# On your VM, add the public key to authorized_keys
mkdir -p ~/.ssh
echo "YOUR_PUBLIC_KEY_CONTENT" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

## 3. Test SSH Connection

```bash
# Test the connection
ssh -i ~/.ssh/github_actions_deploy user@your-vm-ip

# If successful, you should be able to connect without a password
```

## 4. Setup VM Environment

On your VM, prepare the deployment environment:

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/discord-bots.git /home/user/discord-bots
cd /home/user/discord-bots

# Install Node.js and PM2 (if not already installed)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g pm2

# Install Python 3 and pip (if not already installed)
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip

# Make scripts executable
chmod +x scripts/*.sh
```

## 5. Configure GitHub Secrets

In your GitHub repository, go to Settings > Secrets and variables > Actions, then add:

### Repository Secrets Required:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `SSH_PRIVATE_KEY` | Private key content | Contents of `~/.ssh/github_actions_deploy` |
| `SERVER_HOST` | VM IP address or domain | `192.168.1.100` or `myvm.example.com` |
| `SSH_USER` | VM username | `ubuntu` or `user` |
| `PROJECT_PATH` | Full path to project on VM | `/home/user/discord-bots` |

### Bot Token Secrets:

| Secret Name | Description |
|-------------|-------------|
| `BAN_STATS_DISCORD_TOKEN` | Discord token for ban stats bot |
| `RANDOM_COLORS_DISCORD_TOKEN` | Discord token for random colors bot |
| `SUMMARY_BOT_TOKEN` | Discord token for summary bot |
| `FLOWCHART_BOT_TOKEN` | Discord token for flowchart bot |
| `MISTRAL_API_KEY` | Mistral AI API key for summary bot |
| `GUILD_ID` | Your Discord server ID |
| `RANDOM_COLORS_LOG_CHANNEL_ID` | Channel ID for color change logs |

## 6. Initial Deployment

For the first deployment, manually run the setup on your VM:

```bash
cd /home/user/discord-bots
./scripts/setup_venv.sh
```

## 7. Security Best Practices

- Use a dedicated SSH key for GitHub Actions (not your personal key)
- Limit SSH key permissions on the VM
- Consider using a dedicated deployment user with limited privileges
- Regularly rotate SSH keys and bot tokens
- Monitor deployment logs for any suspicious activity

## Troubleshooting

### SSH Connection Issues:
```bash
# Test SSH connection manually
ssh -i ~/.ssh/github_actions_deploy -v user@vm-ip

# Check VM SSH logs
sudo tail -f /var/log/auth.log
```

### Permission Issues:
```bash
# Fix SSH permissions
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh

# Fix project permissions
sudo chown -R user:user /home/user/discord-bots
```

### PM2 Issues:
```bash
# Check PM2 status
pm2 status
pm2 logs

# Restart PM2
pm2 restart all
```