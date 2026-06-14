module.exports = {
  apps: [
    {
      name: "flight-alert",
      script: "uv",
      args: "run python -m flight_alert.cli",
      cwd: __dirname,
      autorestart: true,
      watch: false,
      max_memory_restart: "200M",
      env: {
        PYTHONUNBUFFERED: "1",
        PYTHONPATH: "src",
        UV_CACHE_DIR: ".uv-cache",
      },
    },
  ],
};
