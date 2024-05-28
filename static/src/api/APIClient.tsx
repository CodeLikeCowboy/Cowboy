import axios, { AxiosInstance } from 'axios';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

class APIClient {
  private axiosInstance: AxiosInstance;
  private static config: any = {};

  constructor(config?: any) {
    APIClient.config = config || APIClient.config;

    this.axiosInstance = axios.create({
      baseURL: APIClient.config.api_endpoint,
      headers: {
        'Authorization': `Bearer ${APIClient.config.token}`
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
    const response = await this.axiosInstance.post(uri, data);
    return response.data;
  }

}

export default APIClient;
