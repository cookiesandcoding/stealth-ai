import { create } from 'zustand';

export interface CopilotSuggestion {
  question_id: string;
  category: string;
  question: string;
  confidence: number;
  bullet_answer: string[];
  explanation: string;
  model_used: string;
}

export interface Session {
  id: string;
  title: string;
  transcript: string | null;
  created_at: string;
}

export interface AnalyticsData {
  session_id: string;
  speaking_pace: number;
  clarity_score: number;
  filler_words_count: Record<string, number>;
  knowledge_gaps: string[];
  suggestions: string[];
}

interface CopilotState {
  // Authentication
  userId: string;
  userEmail: string;
  userName: string;
  subscription: string;
  setProfile: (id: string, email: string, name: string, sub: string) => void;

  // Active Live Session
  activeSessionId: string | null;
  isRecording: boolean;
  liveTranscript: string;
  suggestions: CopilotSuggestion[];
  currentSuggestion: CopilotSuggestion | null;
  
  startSession: (sessionId: string) => void;
  stopSession: () => void;
  appendTranscript: (text: string) => void;
  addSuggestion: (suggestion: CopilotSuggestion) => void;
  clearLiveSession: () => void;

  // Screen Analysis
  lastOcrText: string;
  lastOcrProblem: string;
  lastOcrSolution: string;
  setOcrResult: (text: string, problem: string, solution: string) => void;

  // Overlay Configs
  isPinned: boolean;
  overlayTheme: 'dark' | 'light';
  togglePin: () => void;
  setTheme: (theme: 'dark' | 'light') => void;
  overlayActiveTab: 'copilot' | 'screen' | 'settings';
  setOverlayTab: (tab: 'copilot' | 'screen' | 'settings') => void;

  // Mock Interview practice mode
  mockInterviewActive: boolean;
  mockCompany: string;
  mockRole: string;
  mockDifficulty: 'easy' | 'medium' | 'hard';
  mockQuestionIndex: number;
  mockAnswers: string[];
  mockFeedback: string;
  startMockInterview: (company: string, role: string, difficulty: 'easy' | 'medium' | 'hard') => void;
  nextMockQuestion: () => void;
  submitMockAnswer: (answer: string, feedback: string) => void;
  endMockInterview: () => void;

  // Analytics & History
  historicSessions: Session[];
  selectedSession: Session | null;
  selectedAnalytics: AnalyticsData | null;
  setHistoricSessions: (sessions: Session[]) => void;
  setSelectedSession: (session: Session | null) => void;
  setSelectedAnalytics: (analytics: AnalyticsData | null) => void;
}

export const useCopilotStore = create<CopilotState>((set) => ({
  // Authentication initial mockup credentials
  userId: "user-123456789",
  userEmail: "kanishka@stealthai.io",
  userName: "Kanishka Bhatia",
  subscription: "premium",
  setProfile: (id, email, name, sub) => set({ userId: id, userEmail: email, userName: name, subscription: sub }),

  // Active Live Session
  activeSessionId: null,
  isRecording: false,
  liveTranscript: "",
  suggestions: [],
  currentSuggestion: null,

  startSession: (sessionId) => set({
    activeSessionId: sessionId,
    isRecording: true,
    liveTranscript: "",
    suggestions: [],
    currentSuggestion: null
  }),
  stopSession: () => set({ isRecording: false }),
  appendTranscript: (text) => set({ liveTranscript: text }),
  addSuggestion: (suggestion) => set((state) => ({
    suggestions: [suggestion, ...state.suggestions],
    currentSuggestion: suggestion
  })),
  clearLiveSession: () => set({
    activeSessionId: null,
    isRecording: false,
    liveTranscript: "",
    suggestions: [],
    currentSuggestion: null
  }),

  // Screen Analysis
  lastOcrText: "",
  lastOcrProblem: "",
  lastOcrSolution: "",
  setOcrResult: (text, problem, solution) => set({
    lastOcrText: text,
    lastOcrProblem: problem,
    lastOcrSolution: solution
  }),

  // Overlay Configs
  isPinned: false,
  overlayTheme: 'dark',
  togglePin: () => set((state) => ({ isPinned: !state.isPinned })),
  setTheme: (theme) => set({ overlayTheme: theme }),
  overlayActiveTab: 'copilot',
  setOverlayTab: (tab) => set({ overlayActiveTab: tab }),

  // Mock Practice initial models
  mockInterviewActive: false,
  mockCompany: "Google",
  mockRole: "Senior Software Engineer",
  mockDifficulty: "medium",
  mockQuestionIndex: 0,
  mockAnswers: [],
  mockFeedback: "",
  startMockInterview: (company, role, difficulty) => set({
    mockInterviewActive: true,
    mockCompany: company,
    mockRole: role,
    mockDifficulty: difficulty,
    mockQuestionIndex: 0,
    mockAnswers: [],
    mockFeedback: ""
  }),
  nextMockQuestion: () => set((state) => ({ mockQuestionIndex: state.mockQuestionIndex + 1 })),
  submitMockAnswer: (answer, feedback) => set((state) => ({
    mockAnswers: [...state.mockAnswers, answer],
    mockFeedback: feedback
  })),
  endMockInterview: () => set({ mockInterviewActive: false }),

  // History & Analytics
  historicSessions: [],
  selectedSession: null,
  selectedAnalytics: null,
  setHistoricSessions: (sessions) => set({ historicSessions: sessions }),
  setSelectedSession: (session) => set({ selectedSession: session }),
  setSelectedAnalytics: (analytics) => set({ selectedAnalytics: analytics })
}));
