import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const DEMO_USERS = [
  {
    id: '22222222-2222-2222-2222-222222222201',
    name: 'Tech Enthusiast',
    email: 'tech@demo.xai',
    emoji: '💻',
    tagline: 'Electronics lover, gadget researcher',
  },
  {
    id: '22222222-2222-2222-2222-222222222202',
    name: 'Book Lover',
    email: 'books@demo.xai',
    emoji: '📚',
    tagline: 'Voracious reader, non-fiction fan',
  },
  {
    id: '22222222-2222-2222-2222-222222222203',
    name: 'Fashion Fan',
    email: 'fashion@demo.xai',
    emoji: '👗',
    tagline: 'Style-conscious, quality-first shopper',
  },
]

const useAppStore = create(
  persist(
    (set) => ({
      currentUser: DEMO_USERS[0],
      darkMode: true,
      openExplanationId: null,
      demoUsers: DEMO_USERS,
      loggedInUser: null,
      accessToken: null,
      isAdminAuthenticated: false,

      setCurrentUser: (user) =>
        set({ currentUser: user, openExplanationId: null }),

      toggleDarkMode: () =>
        set((s) => ({ darkMode: !s.darkMode })),

      setOpenExplanationId: (id) =>
        set({ openExplanationId: id }),

      closeExplanation: () =>
        set({ openExplanationId: null }),

      login: (user, token) =>
        set({ loggedInUser: { ...user }, accessToken: token }),

      logout: () =>
        set({ loggedInUser: null, accessToken: null, isAdminAuthenticated: false }),

      setAdminAuthenticated: (val) =>
        set({ isAdminAuthenticated: val }),
    }),
    {
      name: 'xai-app-store',
      partialize: (s) => ({
        darkMode: s.darkMode,
        loggedInUser: s.loggedInUser,
        accessToken: s.accessToken,
        // isAdminAuthenticated intentionally omitted — session-only security gate
      }),
    }
  )
)

export default useAppStore
