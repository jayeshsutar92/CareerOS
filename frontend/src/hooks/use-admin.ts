import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminService } from "@/services/admin";

export function useSystemStats() {
  return useQuery({
    queryKey: ["admin", "stats"],
    queryFn: () => adminService.getStatistics(),
  });
}

export function useAdminUsers() {
  return useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => adminService.getUsers(),
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => adminService.deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
    },
  });
}

export function useAdminCompanies() {
  return useQuery({
    queryKey: ["admin", "companies"],
    queryFn: () => adminService.getCompanies(),
  });
}

export function useDeleteAdminCompany() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => adminService.deleteCompany(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "companies"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
    },
  });
}

export function useAdminContacts() {
  return useQuery({
    queryKey: ["admin", "contacts"],
    queryFn: () => adminService.getContacts(),
  });
}

export function useDeleteAdminContact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => adminService.deleteContact(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "contacts"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
    },
  });
}

export function useAdminEmails() {
  return useQuery({
    queryKey: ["admin", "emails"],
    queryFn: () => adminService.getEmails(),
  });
}

export function useDeleteAdminEmail() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => adminService.deleteEmail(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "emails"] });
      queryClient.invalidateQueries({ queryKey: ["admin", "stats"] });
    },
  });
}

export function useAdminTasks() {
  return useQuery({
    queryKey: ["admin", "tasks"],
    queryFn: () => adminService.getTasks(),
  });
}

export function useDeleteAdminTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, taskId }: { userId: string, taskId: string }) => adminService.deleteTask(userId, taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "tasks"] });
    },
  });
}
