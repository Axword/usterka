import type { AxiosRequestConfig } from 'axios';
import AuthHttp from './httpAuth';

class Rest extends AuthHttp {
  async get<T>(url: string, params?: object, config: AxiosRequestConfig = {}): Promise<T> {
    return (await this.http.get<T>(url, { ...config, params })).data;
  }

  async post<T>(url: string, data?: unknown, config: AxiosRequestConfig = {}): Promise<T> {
    return (await this.http.post<T>(url, data, config)).data;
  }

  async patch<T>(url: string, data?: unknown): Promise<T> {
    return (await this.http.patch<T>(url, data)).data;
  }

  async put<T>(url: string, data?: unknown): Promise<T> {
    return (await this.http.put<T>(url, data)).data;
  }

  async delete<T = void>(url: string): Promise<T> {
    return (await this.http.delete<T>(url)).data;
  }

  async blob(url: string): Promise<Blob> {
    return (await this.http.get<Blob>(url, { responseType: 'blob' })).data;
  }

  /** multipart/form-data - Content-Type ustawia przeglądarka. */
  async upload<T>(url: string, form: FormData, onProgress?: (p: number) => void): Promise<T> {
    return (
      await this.http.post<T>(url, form, {
        headers: { 'Content-Type': undefined },
        onUploadProgress: (e) => onProgress && e.total && onProgress(e.loaded / e.total),
      })
    ).data;
  }
}

export const rest = new Rest();
export default Rest;
