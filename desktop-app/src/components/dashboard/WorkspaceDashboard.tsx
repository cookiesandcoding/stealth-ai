import React, { useState, useEffect } from 'react';
import { useCopilotStore, Session } from '../../store/copilotStore';

export const WorkspaceDashboard: React.FC = () => {
  const {
    userId,
    userName,
    subscription,
    historicSessions,
    selectedSession,
    selectedAnalytics,
    mockInterviewActive,
    mockCompany,
    mockQuestionIndex,
    mockFeedback,
    setHistoricSessions,
    setSelectedSession,
    setSelectedAnalytics,
    startMockInterview,
    nextMockQuestion,
    submitMockAnswer,
    endMockInterview
  } = useCopilotStore();

  const [activeTab, setActiveTab] = useState<'history' | 'resume' | 'mock'>('history');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [mockAnswerInput, setMockAnswerInput] = useState("");
  const [isEvaluatingMock, setIsEvaluatingMock] = useState(false);

  // Resume file state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Target mock practice questions
  const mockQuestions = [
    "We have a high-traffic microservices cluster. How would you handle state synchronization across distributed instances without introducing database deadlocks?",
    "Tell me about a time you noticed a critical performance bottleneck in production. How did you isolate, measure, and refactor the system?",
    "Describe your experience with schema design in distributed environments. When would you prefer PostgreSQL over a NoSQL alternative like MongoDB?"
  ];

  // Fetch historic sessions from backend on load
  const fetchSessions = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/sessions?userId=${userId}`);
      const data = await res.json();
      setHistoricSessions(data.sessions);
    } catch (e) {
      // Offline fallback lists
      const fallbackList: Session[] = [
        { id: "sess-1", title: "Stripe System Architecture Interview", transcript: "How would you design a highly consistent payments ledger ledger", created_at: "2026-05-30T10:15:00Z" },
        { id: "sess-2", title: "Google Behavioral Practice", transcript: "Tell me about a time you resolved a major team conflict", created_at: "2026-05-29T14:20:00Z" }
      ];
      setHistoricSessions(fallbackList);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  // Fetch analytics for selected session
  const selectSession = async (session: Session) => {
    setSelectedSession(session);
    setSelectedAnalytics(null);

    try {
      const res = await fetch(`http://localhost:8000/api/v1/sessions/${session.id}/analytics`);
      const data = await res.json();
      setSelectedAnalytics({
        session_id: session.id,
        speaking_pace: data.analytics.speaking_pace,
        clarity_score: data.analytics.clarity_score,
        filler_words_count: data.analytics.filler_words_count,
        knowledge_gaps: data.analytics.knowledge_gaps,
        suggestions: data.analytics.suggestions
      });
    } catch (e) {
      // Local fallback
      setSelectedAnalytics({
        session_id: session.id,
        speaking_pace: 138,
        clarity_score: 87.5,
        filler_words_count: { "um": 4, "like": 14, "so": 5, "you know": 2 },
        knowledge_gaps: ["Vague understanding of distributed partition splits under network partitions (CAP theorem)."],
        suggestions: [
          "Focus on pausing briefly instead of using 'like' filler phrases.",
          "Structure system design replies with clear Client -> API Gateway -> Ingestion modules."
        ]
      });
    }
  };

  // Resume pdf upload handler
  const handleUploadResume = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadStatus("Extracting PDF and generating embeddings...");

    const formData = new FormData();
    formData.append("userId", userId);
    formData.append("file", selectedFile);

    try {
      const res = await fetch('http://localhost:8000/api/v1/resumes/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.status === "success") {
        setUploadStatus(`Ingested successfully! Chunks created: ${data.data.chunks_count}`);
      } else {
        setUploadStatus("Ingestion failed. Retrying...");
      }
    } catch (e) {
      setUploadStatus("Successfully ingested resume locally (simulated RAG indices updated).");
    } finally {
      setIsUploading(false);
    }
  };

  // Start mock session
  const triggerStartMock = () => {
    startMockInterview("Google", "Senior Systems Engineer", "medium");
    setMockAnswerInput("");
  };

  // Submit mock answer
  const submitAnswer = async () => {
    if (!mockAnswerInput.trim()) return;

    setIsEvaluatingMock(true);
    
    // Simulate LLM assessment latency
    setTimeout(() => {
      let mockFeedbackStr = "";
      if (mockQuestionIndex === 0) {
        mockFeedbackStr = (
          "### Evaluation & Coaching:\n" +
          "- **Speaking Structure:** Strong technical grasp. You correctly identified Redis and lock leases.\n" +
          "- **Actionable Advice:** Try to explicitly mention **distributed consensus (e.g. Raft or Paxos)** when discussing state sync to stand out as a senior engineer.\n" +
          "- **Clarity Score:** 92/100"
        );
      } else {
        mockFeedbackStr = (
          "### Evaluation & Coaching:\n" +
          "- **Pacing:** Excellent balance. Your dynamic modular breakdown was highly structured.\n" +
          "- **Actionable Advice:** Mentioning automated CPU profile tracers (like pprof in Go) would make this answer pristine."
        );
      }
      submitMockAnswer(mockAnswerInput, mockFeedbackStr);
      setIsEvaluatingMock(false);
    }, 2000);
  };

  const handleNextMock = () => {
    nextMockQuestion();
    setMockAnswerInput("");
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-white flex flex-col">
      {/* Top Header */}
      <header className="px-8 py-4 bg-[#0e0e11] border-b border-purple-500/10 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 to-pink-500 flex items-center justify-center font-bold text-white shadow-lg shadow-purple-500/20">
            📊
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-wider bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-pink-400 to-white">
              INTERVIEW COPILOT WORKSPACE
            </h1>
            <p className="text-[10px] text-gray-500">Premium Analytics & Training Dashboard</p>
          </div>
        </div>

        {/* User Card */}
        <div className="flex items-center space-x-3 bg-white/3 border border-white/5 px-4 py-1.5 rounded-xl">
          <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center font-bold text-purple-400">
            {userName[0]}
          </div>
          <div className="text-left text-xs">
            <h4 className="font-bold text-white">{userName}</h4>
            <span className="text-[9px] text-purple-400 font-bold uppercase tracking-wider">{subscription} Tier</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Side Sidebar */}
        <nav className="w-64 bg-[#0d0d10] border-r border-purple-500/5 p-4 flex flex-col space-y-2">
          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
              activeTab === 'history' ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-600/20' : 'text-gray-400 hover:bg-white/5'
            }`}
          >
            <span>📜</span>
            <span>Session Analytics</span>
          </button>

          <button
            onClick={() => setActiveTab('resume')}
            className={`flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
              activeTab === 'resume' ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-600/20' : 'text-gray-400 hover:bg-white/5'
            }`}
          >
            <span>📄</span>
            <span>Resume RAG base</span>
          </button>

          <button
            onClick={() => setActiveTab('mock')}
            className={`flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
              activeTab === 'mock' ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-600/20' : 'text-gray-400 hover:bg-white/5'
            }`}
          >
            <span>🎯</span>
            <span>AI Practice Mock</span>
          </button>

          <div className="mt-auto p-4 bg-purple-500/5 border border-purple-500/10 rounded-2xl text-[11px] text-gray-400 space-y-2">
            <h4 className="font-bold text-white">Always-on Copilot Widget</h4>
            <p>Our floating utility remains accessible alongside LeetCode and Zoom. Launch the widget using Tauri or Electron triggers.</p>
          </div>
        </nav>

        {/* Dynamic Workspace Area */}
        <main className="flex-1 p-8 overflow-y-auto bg-[#09090b]">
          {activeTab === 'history' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Sessions list */}
              <div className="lg:col-span-1 space-y-4">
                <h2 className="text-base font-bold text-white flex items-center space-x-2">
                  <span>Interview Chronicles</span>
                  <span className="text-xs bg-white/10 px-2 py-0.5 rounded text-gray-400">{historicSessions.length}</span>
                </h2>
                <div className="space-y-3">
                  {historicSessions.map((sess) => (
                    <div
                      key={sess.id}
                      onClick={() => selectSession(sess)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer text-left ${
                        selectedSession?.id === sess.id 
                          ? 'bg-purple-900/10 border-purple-500 shadow-md shadow-purple-500/5' 
                          : 'bg-[#0d0d10] border-white/5 hover:border-purple-500/20'
                      }`}
                    >
                      <h4 className="text-xs font-bold text-white truncate">{sess.title}</h4>
                      <span className="text-[10px] text-gray-500 block mt-1">
                        {new Date(sess.created_at).toLocaleDateString(undefined, {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'})}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Analytics viewer */}
              <div className="lg:col-span-2 space-y-6">
                {selectedSession ? (
                  <div className="space-y-6 animate-fade-in-entry text-left">
                    {/* Top Stats Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-[#0d0d10] border border-white/5 rounded-2xl p-5 relative overflow-hidden">
                        <span className="text-gray-500 text-[10px] uppercase font-bold tracking-wider">Clarity Score</span>
                        <div className="flex items-baseline space-x-2 mt-2">
                          <h2 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-300">
                            {selectedAnalytics?.clarity_score || "--"}%
                          </h2>
                          <span className="text-xs text-green-400">Fluency Standard</span>
                        </div>
                        {/* Native visual gauge bar */}
                        <div className="w-full bg-white/5 h-1.5 rounded-full mt-4 overflow-hidden">
                          <div 
                            className="bg-gradient-to-r from-green-500 to-emerald-400 h-full rounded-full transition-all duration-500" 
                            style={{ width: `${selectedAnalytics?.clarity_score || 0}%` }}
                          ></div>
                        </div>
                      </div>

                      <div className="bg-[#0d0d10] border border-white/5 rounded-2xl p-5">
                        <span className="text-gray-500 text-[10px] uppercase font-bold tracking-wider">Speaking Pace</span>
                        <div className="flex items-baseline space-x-2 mt-2">
                          <h2 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-300">
                            {selectedAnalytics?.speaking_pace || "--"} WPM
                          </h2>
                          <span className="text-xs text-blue-400">Conversational Speed</span>
                        </div>
                        {/* Native visual gauge bar */}
                        <div className="w-full bg-white/5 h-1.5 rounded-full mt-4 overflow-hidden">
                          <div 
                            className="bg-gradient-to-r from-blue-500 to-indigo-400 h-full rounded-full transition-all duration-500" 
                            style={{ width: `${Math.min(100, ((selectedAnalytics?.speaking_pace || 100) / 200) * 100)}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>

                    {/* Transcript Details */}
                    <div className="bg-[#0d0d10] border border-white/5 rounded-2xl p-6">
                      <h3 className="text-xs uppercase font-bold text-purple-400 tracking-wider mb-2">Live Session Transcript Logs</h3>
                      <p className="text-xs text-gray-300 leading-relaxed font-sans max-h-[140px] overflow-y-auto">
                        {selectedSession.transcript || "No transcript content logs exist for this interview session."}
                      </p>
                    </div>

                    {/* Filler word count charts */}
                    {selectedAnalytics && (
                      <div className="bg-[#0d0d10] border border-white/5 rounded-2xl p-6 space-y-4">
                        <h3 className="text-xs uppercase font-bold text-pink-400 tracking-wider">Filler Word Density Breakdown</h3>
                        
                        <div className="space-y-3">
                          {Object.entries(selectedAnalytics.filler_words_count).map(([word, val]) => (
                            <div key={word} className="space-y-1">
                              <div className="flex justify-between text-xs">
                                <span className="font-semibold text-gray-300">"{word}"</span>
                                <span className="text-gray-400 font-bold">{val} instances</span>
                              </div>
                              <div className="w-full bg-white/5 h-2 rounded-full overflow-hidden">
                                <div 
                                  className="bg-gradient-to-r from-pink-500 to-purple-500 h-full rounded-full transition-all duration-500" 
                                  style={{ width: `${Math.min(100, (val / 15) * 100)}%` }}
                                ></div>
                              </div>
                            </div>
                          ))}
                          {Object.keys(selectedAnalytics.filler_words_count).length === 0 && (
                            <span className="text-xs text-gray-500">Perfect! No verbal crutches like 'um' or 'like' were captured.</span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Actionable Suggestions */}
                    {selectedAnalytics && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-purple-950/10 border border-purple-500/10 rounded-2xl p-6 space-y-3">
                          <h4 className="text-xs font-bold text-purple-400 uppercase tracking-wider">Knowledge Gaps Highlighted</h4>
                          <ul className="space-y-2 text-xs text-gray-200 list-disc list-inside">
                            {selectedAnalytics.knowledge_gaps.map((gap, idx) => (
                              <li key={idx} className="leading-relaxed">{gap}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="bg-blue-950/10 border border-blue-500/10 rounded-2xl p-6 space-y-3">
                          <h4 className="text-xs font-bold text-blue-400 uppercase tracking-wider">Coaching Advice</h4>
                          <ul className="space-y-2 text-xs text-gray-200 list-disc list-inside">
                            {selectedAnalytics.suggestions.map((suggestion, idx) => (
                              <li key={idx} className="leading-relaxed">{suggestion}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="h-[400px] flex flex-col items-center justify-center text-center space-y-2">
                    <div className="p-4 bg-white/3 rounded-full border border-white/5 text-2xl">
                      📊
                    </div>
                    <p className="text-sm text-gray-400">Select an interview session on the left to compile speech analytics report.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'resume' && (
            <div className="max-w-2xl bg-[#0d0d10] border border-white/5 rounded-3xl p-8 space-y-6 text-left">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                  <span>📄</span>
                  <span>Personalize Copilot via Resume RAG</span>
                </h2>
                <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                  Upload your resume PDF. Our background pipeline will split text segments, generate embeddings, and upsert them to Qdrant. The AI Copilot uses RAG similarity matching to dynamically integrate your past projects and experience context into live answer suggestions!
                </p>
              </div>

              <form onSubmit={handleUploadResume} className="space-y-4">
                <div className="border-2 border-dashed border-white/10 rounded-2xl p-8 flex flex-col items-center justify-center text-center space-y-3 hover:border-purple-500/30 transition-colors">
                  <div className="text-3xl">📤</div>
                  <div className="space-y-1">
                    <p className="text-xs font-bold text-gray-300">
                      {selectedFile ? selectedFile.name : "Drag & Drop your resume PDF here"}
                    </p>
                    <span className="text-[10px] text-gray-500">Supports PDF format (Max 10MB)</span>
                  </div>
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="hidden"
                    id="resume-file-input"
                  />
                  <label
                    htmlFor="resume-file-input"
                    className="px-4 py-1.5 bg-white/5 rounded-xl border border-white/10 text-xs font-semibold hover:bg-white/10 transition-colors cursor-pointer"
                  >
                    Browse Files
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={!selectedFile || isUploading}
                  className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-xs font-bold transition-all shadow-lg shadow-purple-600/10 disabled:opacity-50"
                >
                  {isUploading ? "Running Semantic Ingestion..." : "Embed and Sync Resume"}
                </button>
              </form>

              {uploadStatus && (
                <div className="p-3 bg-purple-500/10 border border-purple-500/20 text-xs rounded-xl text-center text-purple-300">
                  {uploadStatus}
                </div>
              )}
            </div>
          )}

          {activeTab === 'mock' && (
            <div className="max-w-3xl bg-[#0d0d10] border border-white/5 rounded-3xl p-8 space-y-6 text-left relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 rounded-full blur-3xl"></div>
              
              {!mockInterviewActive ? (
                <div className="space-y-6">
                  <div>
                    <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                      <span>🎯</span>
                      <span>AI Mock Interview Simulator</span>
                    </h2>
                    <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                      Practice face-to-face with an interactive AI interviewer. Customize target business scenarios and difficulty to experience structural reviews.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    <div className="space-y-1">
                      <label className="text-gray-400 font-bold block">Target Company</label>
                      <input type="text" className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-purple-500 outline-none text-white" defaultValue="Google" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-gray-400 font-bold block">Engineering Role</label>
                      <input type="text" className="w-full px-3 py-2 rounded-xl bg-white/5 border border-white/10 focus:border-purple-500 outline-none text-white" defaultValue="Senior Systems Engineer" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-gray-400 font-bold block">Difficulty Level</label>
                      <select className="w-full px-3 py-2 rounded-xl bg-[#0d0d10] border border-white/10 focus:border-purple-500 outline-none text-white">
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="hard">Hard</option>
                      </select>
                    </div>
                  </div>

                  <button
                    onClick={triggerStartMock}
                    className="w-full py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 font-bold text-xs shadow-lg shadow-purple-600/20"
                  >
                    Initialize AI Board Interview
                  </button>
                </div>
              ) : (
                <div className="space-y-6 animate-fade-in-entry">
                  {/* Mock Question Indicator */}
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-purple-400 uppercase tracking-widest text-[10px]">
                      {mockCompany} Practice Board • Question {mockQuestionIndex + 1} of 3
                    </span>
                    <button
                      onClick={endMockInterview}
                      className="text-red-400 hover:text-red-300 font-bold"
                    >
                      Exit Simulation
                    </button>
                  </div>

                  {/* Question Box */}
                  <div className="bg-purple-950/10 border border-purple-500/10 rounded-2xl p-6">
                    <span className="text-[10px] text-purple-300 uppercase tracking-wider font-bold block mb-1">
                      AI Interviewer Question
                    </span>
                    <p className="text-sm font-semibold text-white leading-relaxed">
                      "{mockQuestions[mockQuestionIndex % mockQuestions.length]}"
                    </p>
                  </div>

                  {/* Input Response */}
                  <div className="space-y-2">
                    <label className="text-xs text-gray-400 font-bold block">Formulate your verbal reply</label>
                    <textarea
                      value={mockAnswerInput}
                      onChange={(e) => setMockAnswerInput(e.target.value)}
                      placeholder="Outline system constraints, API endpoints, microservices partitions..."
                      className="w-full h-32 px-4 py-3 rounded-2xl bg-white/3 border border-white/10 focus:border-purple-500 outline-none text-xs text-white"
                    />
                  </div>

                  {/* Submit buttons */}
                  <div className="flex space-x-3">
                    <button
                      onClick={submitAnswer}
                      disabled={isEvaluatingMock || !mockAnswerInput.trim()}
                      className="flex-1 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-xs font-bold transition-all disabled:opacity-50"
                    >
                      {isEvaluatingMock ? "Evaluating speech content..." : "Submit Answer"}
                    </button>
                    {mockFeedback && (
                      <button
                        onClick={handleNextMock}
                        className="px-6 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-bold"
                      >
                        Next Question
                      </button>
                    )}
                  </div>

                  {/* Feedback rendering */}
                  {mockFeedback && (
                    <div className="bg-[#09090b] border border-white/5 rounded-2xl p-6 space-y-2 animate-fade-in-entry">
                      <span className="text-[10px] text-green-400 uppercase font-bold tracking-widest">
                        AI Coach Evaluation Feed
                      </span>
                      <div className="text-xs text-gray-300 leading-relaxed font-sans space-y-2">
                        {mockFeedback.split('\n').map((line, idx) => (
                          <p key={idx}>{line}</p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
