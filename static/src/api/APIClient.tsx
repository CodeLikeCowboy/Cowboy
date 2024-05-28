import axios, { AxiosInstance } from 'axios';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

class APIClient {
  private axiosInstance: AxiosInstance;

  constructor() {
    this.axiosInstance = axios.create({
      // TODO: make both of these read from config file in public
      baseURL: 'http://18.223.150.134:3000',
      headers: {
        'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjIwMjUyMzI2MDEuMjE4MDc3LCJlbWFpbCI6InRlc3R1c2VyNkBnbWFpbC5jb20ifQ.98BU_JcTSUi9I5aGfczKZVu3uTWDmfMj8vz83tpAo-M'
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
