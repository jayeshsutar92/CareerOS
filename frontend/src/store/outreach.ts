import { create } from "zustand";

interface OutreachState {
  selectedRecipientIds: string[];
  toggleRecipient: (id: string) => void;
  selectAllRecipients: (ids: string[]) => void;
  deselectAllRecipients: () => void;
  clearRecipients: () => void;
}

export const useOutreachStore = create<OutreachState>((set) => ({
  selectedRecipientIds: [],
  toggleRecipient: (id) =>
    set((state) => ({
      selectedRecipientIds: state.selectedRecipientIds.includes(id)
        ? state.selectedRecipientIds.filter((recId) => recId !== id)
        : [...state.selectedRecipientIds, id],
    })),
  selectAllRecipients: (ids) =>
    set((state) => {
      const newIds = new Set([...state.selectedRecipientIds, ...ids]);
      return { selectedRecipientIds: Array.from(newIds) };
    }),
  deselectAllRecipients: () => set({ selectedRecipientIds: [] }),
  clearRecipients: () => set({ selectedRecipientIds: [] }),
}));
