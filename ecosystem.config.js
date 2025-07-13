module.exports = {
  apps: [
    {
      name: 'ban-stats-bot',
      script: './ban_stats/src/main.py',
      interpreter: './venv/bin/python',
      cwd: './ban_stats',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/ban-stats-error.log',
      out_file: './logs/ban-stats-out.log',
      log_file: './logs/ban-stats.log',
      time: true,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      instances: 1,
      exec_mode: 'fork'
    },
    {
      name: 'random-colors-bot',
      script: './random_colors/src/main.py',
      interpreter: './venv/bin/python',
      cwd: './random_colors',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/random-colors-error.log',
      out_file: './logs/random-colors-out.log',
      log_file: './logs/random-colors.log',
      time: true,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      instances: 1,
      exec_mode: 'fork'
    },
    {
      name: 'summary-bot',
      script: './summary/src/summarizer_bot.py',
      interpreter: './venv/bin/python',
      cwd: './summary',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/summary-error.log',
      out_file: './logs/summary-out.log',
      log_file: './logs/summary.log',
      time: true,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      instances: 1,
      exec_mode: 'fork'
    },
    {
      name: 'flowchart-bot',
      script: './flowchart/src/main.py',
      interpreter: './venv/bin/python',
      cwd: './flowchart',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/flowchart-error.log',
      out_file: './logs/flowchart-out.log',
      log_file: './logs/flowchart.log',
      time: true,
      autorestart: true,
      watch: false,
      max_memory_restart: '256M',
      instances: 1,
      exec_mode: 'fork'
    }
  ]
};