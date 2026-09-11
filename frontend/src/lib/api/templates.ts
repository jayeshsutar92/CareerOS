import { api } from "@/services/api"

export interface Template {
  id: string
  name: string
  subject: string
  body: string
  created_at: string
  updated_at: string
}

export const templatesApi = {
  list: async (): Promise<Template[]> => {
    const response = await api.get<Template[]>("/templates")
    return response.data
  },
  
  get: async (id: string): Promise<Template> => {
    const response = await api.get<Template>(`/templates/${id}`)
    return response.data
  }
}
