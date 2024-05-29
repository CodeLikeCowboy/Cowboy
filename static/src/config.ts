interface Config {
    token: string
    api_endpoint: string
}

async function readConfig(): Promise<Config> {
    const response = await fetch('/build/config.json');
    if (!response.ok) {
      throw new Error('Failed to fetch config.json');
    }
    const config: Config = await response.json();
    return config;
  }
  

export {readConfig};

