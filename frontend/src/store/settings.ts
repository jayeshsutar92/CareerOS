import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface SettingsState {
  profile: {
    name: string;
    email: string;
    designation: string;
    bio: string;
    skills: string;
    portfolioLinks: string;
    githubLink: string;
    linkedinLink: string;
  };
  outreach: {
    emailSignature: string;
    defaultTone: string;
    customInstructions: string;
    senderPreferences: string;
  };
  updateProfile: (profile: Partial<SettingsState["profile"]>) => void;
  updateOutreach: (outreach: Partial<SettingsState["outreach"]>) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      profile: {
        name: "",
        email: "",
        designation: "",
        bio: "",
        skills: "",
        portfolioLinks: "",
        githubLink: "",
        linkedinLink: "",
      },
      outreach: {
        emailSignature: "",
        defaultTone: "Professional",
        customInstructions: "",
        senderPreferences: "",
      },
      updateProfile: (profile) =>
        set((state) => ({ profile: { ...state.profile, ...profile } })),
      updateOutreach: (outreach) =>
        set((state) => ({ outreach: { ...state.outreach, ...outreach } })),
    }),
    {
      name: "email-shooter-settings",
    }
  )
);
