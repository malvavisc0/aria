---
layout: default
title: Advanced Features
---

# Advanced Features

This guide covers the advanced features and capabilities of Aria that power users might find useful.

## Custom Model Configuration

Aria uses Ollama to run AI models. You can customize the model behavior by adjusting parameters in your `.env` file:

```env
OLLAMA_MODEL_ID=cogito:14b
OLLAMA_MODEL_TEMPERATURE=0.7
OLLAMA_MODEL_CONTEXT_LENGTH=8192
```

### Supported Models

Aria works with any model supported by Ollama, including:

- Llama 2
- Mistral
- Vicuna
- Orca
- Wizard
- And many others

To use a different model, simply change the `OLLAMA_MODEL_ID` in your `.env` file.

## API Integration

Aria provides a REST API that allows you to integrate it with other applications:

### Authentication

```bash
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "your-username", "password": "your-password"}'
```

### Chat Completion

```bash
curl -X POST http://localhost:8000/api/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "stream": true
  }'
```

## Custom Plugins

Aria supports custom plugins that extend its functionality. Plugins are Python modules that implement specific interfaces:

```python
from aria.plugins import AriaPlugin

class MyCustomPlugin(AriaPlugin):
    def __init__(self):
        super().__init__(
            name="my_custom_plugin",
            description="A custom plugin for Aria"
        )
    
    async def execute(self, query, context):
        # Your plugin logic here
        return {"result": "Custom plugin response"}
```

Place your plugin in the `plugins` directory and restart Aria to load it.

## Advanced Search Configuration

SearXNG, the search engine used by Aria, can be customized by editing the `searxng/settings.yml` file:

```yaml
search:
  safe_search: 0  # 0: None, 1: Moderate, 2: Strict
  autocomplete: 'google'
  default_lang: 'en'
```

## Performance Tuning

For better performance on resource-constrained systems:

1. Reduce the number of workers in `searxng/uwsgi.ini`:
   ```ini
   workers = 2
   threads = 2
   ```

2. Use a smaller model by setting `OLLAMA_MODEL_ID` to a more compact model:
   ```env
   OLLAMA_MODEL_ID=tinyllama:1.1b
   ```

3. Adjust Redis cache settings in your `docker-compose.yml`:
   ```yaml
   redis:
     command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
   ```

## Backup and Restore

### Backup

To backup your Aria data:

```bash
docker-compose stop
tar -czvf aria-backup.tar.gz data/
docker-compose start
```

### Restore

To restore from a backup:

```bash
docker-compose stop
rm -rf data/
tar -xzvf aria-backup.tar.gz
docker-compose start
```

## Troubleshooting

### Logs

View logs for troubleshooting:

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs aria
```

### Debug Mode

Enable debug mode for more detailed logs:

```env
DEBUG_MODE=true
```

### Common Issues

1. **Connection refused to Ollama**:
   - Ensure Ollama is running and accessible at the URL specified in `OLLAMA_URL`
   - Check network connectivity between the Aria container and Ollama

2. **High memory usage**:
   - Use a smaller model
   - Reduce the context length with `OLLAMA_MODEL_CONTEXT_LENGTH`

3. **Slow responses**:
   - Check CPU usage and consider using a more powerful machine
   - Reduce the number of concurrent users

## Next Steps

- Learn about [contributing](/aria/contributing.html) to Aria
- Return to the [usage guide](/aria/usage.html)
- Check the [configuration options](/aria/configuration.html)
