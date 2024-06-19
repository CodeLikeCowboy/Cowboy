export interface Config {
    jwt_token: string
    api_endpoint: string
}

async function fetchConfig(): Promise<Config> {
    const response = await fetch('/config.json');
    if (!response.ok) {
      throw new Error('Failed to fetch config.json');
    }
    const config: Config = await response.json();
    return config;
  }
  

export { fetchConfig };

