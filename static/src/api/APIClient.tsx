import axios, { AxiosInstance } from 'axios';
import { Config } from 'config';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

class APIClient {
  private axiosInstance: AxiosInstance;

  constructor(config: Config) {
    console.log("Config: ", config.jwt_token, config.api_endpoint)
    this.axiosInstance = axios.create({
      baseURL: config.api_endpoint,
      headers: {
        'Authorization': `Bearer ${config.jwt_token}`
      }
    });
  
    this.axiosInstance.interceptors.response.use(
      response => response,
      error => {
        if (error.response && error.response.status === 401) {
            toast.error('Unauthorized access. Please log in via the cowboy python cli');
        }
        else if (error.response && error.response.status === 422) {
          toast.error(`Server Error: ${JSON.stringify(error.response.data, null, 2)}`);
        }
        return Promise.reject(error);
      }
    );  
  }
  
  public async get(uri: string, query: string = "") {    
    console.log("GET: ", uri);
    // remove backslash so our query string can be joined properly
    if (uri.endsWith('/')) {
        uri = uri.slice(0, -1);
    }
    if (query) {
        uri = `${uri}?${query}`;
    }

    const response = await this.axiosInstance.get(uri);
    return response.data;
  }

  public async post(uri: string, data: any) {
    console.log("POST: ", uri);

    const response = await this.axiosInstance.post(uri, data);
    return response.data;
  }

}

export default APIClient;
