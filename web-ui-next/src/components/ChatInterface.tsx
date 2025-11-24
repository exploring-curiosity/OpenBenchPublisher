"use client";

import { useState, useEffect, useRef } from 'react';
import { Send, Plus, MessageSquare, Trash2, Clock, CheckCircle, Loader2, Download } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  plan?: DatasetPlan;
  request_id?: string;
}

interface DatasetPlan {
  action: string;
  query: string;
  classes: string[];
  total_items: number;
  data_type: string;
}

interface Chat {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
}

interface ChatInterfaceProps {
  onPlanGenerated?: (plan: any) => void;
}

interface SamplingStatus {
  request_id: string;
  status: string;
  progress: number;
  total: number;
  samples?: any[];
}

export function ChatInterface({ onPlanGenerated }: ChatInterfaceProps) {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChat, setActiveChat] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingChats, setLoadingChats] = useState(true);
  const [executingPlan, setExecutingPlan] = useState(false);
  const [samplingStatus, setSamplingStatus] = useState<Record<string, SamplingStatus>>({});
  const messageIdCounter = useRef(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chats, activeChat]);

  // Load chats from backend
  useEffect(() => {
    loadChats();
  }, []);

  // Load active chat messages
  useEffect(() => {
    if (activeChat && !activeChat.startsWith('temp-')) {
      loadChatMessages(activeChat);
    }
  }, [activeChat]);

  const loadChats = async () => {
    try {
      const res = await fetch('/api/chats');
      if (res.ok) {
        const data = await res.json();
        // Ensure each chat has a messages array
        const chatsWithMessages = (data.chats || []).map((chat: any) => ({
          ...chat,
          messages: chat.messages || []
        }));
        setChats(chatsWithMessages);
        if (chatsWithMessages.length > 0 && !activeChat) {
          setActiveChat(chatsWithMessages[0].id);
        }
      }
    } catch (error) {
      console.error('Failed to load chats:', error);
    } finally {
      setLoadingChats(false);
    }
  };

  const loadChatMessages = async (chatId: string) => {
    try {
      const res = await fetch(`/api/chats/${chatId}`);
      if (res.ok) {
        const data = await res.json();
        // Backend now provides unique IDs for all messages
        setChats(prevChats => prevChats.map(chat => 
          chat.id === chatId 
            ? { ...chat, messages: data.messages || [] }
            : chat
        ));
      }
    } catch (error) {
      console.error('Failed to load chat messages:', error);
    }
  };

  const createNewChat = () => {
    const newChatId = `temp-${Date.now()}`;
    const newChat: Chat = {
      id: newChatId,
      title: 'New Chat',
      messages: [],
      createdAt: new Date().toISOString(),
    };
    setChats([newChat, ...chats]);
    setActiveChat(newChatId);
  };

  const deleteChat = async (chatId: string) => {
    if (chats.length === 1) return;
    
    try {
      await fetch(`/api/chats/${chatId}`, { method: 'DELETE' });
      const filtered = chats.filter(c => c.id !== chatId);
      setChats(filtered);
      if (activeChat === chatId) {
        setActiveChat(filtered[0]?.id || null);
      }
    } catch (error) {
      console.error('Failed to delete chat:', error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `msg-${Date.now()}-${++messageIdCounter.current}`,
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    // Optimistically add user message
    setChats(prevChats => prevChats.map(chat => {
      if (chat.id === activeChat) {
        return {
          ...chat,
          messages: [...chat.messages, userMessage],
        };
      }
      return chat;
    }));

    setInput('');
    setIsLoading(true);

    try {
      // Call chat API with chat_id
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.content,
          chat_id: activeChat?.startsWith('temp-') ? null : activeChat
        })
      });

      if (!res.ok) {
        throw new Error('Chat API failed');
      }

      const data = await res.json();
      
      const assistantMessage: Message = {
        id: `msg-${Date.now()}-${++messageIdCounter.current}`,
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        plan: data.plan || undefined,
        request_id: data.request_id
      };

      // Update chat with response and new chat_id if it was temp
      setChats(prevChats => prevChats.map(chat => {
        // Only update the active chat
        if (chat.id === activeChat) {
          const updatedChat = {
            ...chat,
            id: data.chat_id || chat.id,
            title: chat.title === 'New Chat' && data.chat_id ? (userMessage.content.slice(0, 50) + (userMessage.content.length > 50 ? '...' : '')) : chat.title,
            messages: [...chat.messages.filter(m => m.id !== userMessage.id), userMessage, assistantMessage],
          };
          
          // Update active chat if it was temp
          if (activeChat?.startsWith('temp-') && data.chat_id) {
            setActiveChat(data.chat_id);
          }
          
          return updatedChat;
        }
        return chat;
      }));

    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: `msg-${Date.now()}-${++messageIdCounter.current}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      };
      
      setChats(prevChats => prevChats.map(chat => {
        if (chat.id === activeChat) {
          return {
            ...chat,
            messages: [...chat.messages, errorMessage],
          };
        }
        return chat;
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const executePlan = async (plan: DatasetPlan) => {
    setExecutingPlan(true);
    try {
      // Call the plan-and-sample endpoint
      const res = await fetch('/api/plan-and-sample', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: plan.query,
          total_items: plan.total_items,
          data_type: plan.data_type
        })
      });

      if (!res.ok) {
        throw new Error('Failed to execute plan');
      }

      const result = await res.json();
      const requestId = result.request_id;
      
      // Start polling for status
      if (requestId) {
        setSamplingStatus(prev => ({
          ...prev,
          [requestId]: {
            request_id: requestId,
            status: 'running',
            progress: 0,
            total: plan.total_items
          }
        }));
        
        pollSamplingStatus(requestId, activeChat || '');
      }
      
      // Add success message to chat
      const successMessage: Message = {
        id: `msg-${Date.now()}-${++messageIdCounter.current}`,
        role: 'assistant',
        content: `🚀 Started dataset sampling! Request ID: ${requestId}`,
        timestamp: new Date().toISOString(),
        request_id: requestId
      };

      setChats(prevChats => prevChats.map(chat => {
        if (chat.id === activeChat) {
          return {
            ...chat,
            messages: [...chat.messages, successMessage],
          };
        }
        return chat;
      }));

      if (onPlanGenerated) {
        onPlanGenerated(result);
      }
    } catch (error) {
      console.error('Execute plan error:', error);
      const errorMessage: Message = {
        id: `msg-${Date.now()}-${++messageIdCounter.current}`,
        role: 'assistant',
        content: '❌ Failed to execute plan. Please try again or use the Build Tool manually.',
        timestamp: new Date().toISOString(),
      };
      
      setChats(prevChats => prevChats.map(chat => {
        if (chat.id === activeChat) {
          return {
            ...chat,
            messages: [...chat.messages, errorMessage],
          };
        }
        return chat;
      }));
    } finally {
      setExecutingPlan(false);
    }
  };

  const pollSamplingStatus = async (requestId: string, chatId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/download-progress?request_id=${requestId}`);
        if (res.ok) {
          const data = await res.json();
          
          setSamplingStatus(prev => ({
            ...prev,
            [requestId]: {
              request_id: requestId,
              status: data.status || 'running',
              progress: data.downloaded || 0,
              total: data.total || 0,
              samples: data.samples
            }
          }));
          
          // Stop polling if completed
          if (data.status === 'completed' || data.downloaded >= data.total) {
            clearInterval(pollInterval);
            
            // Add completion message using callback to avoid stale closure
            const completionMessage: Message = {
              id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
              role: 'assistant',
              content: `✅ Dataset sampling completed! ${data.downloaded} samples ready.\n\n📂 Go to the **Datasets** tab to review samples and start the full download when ready.`,
              timestamp: new Date().toISOString(),
              request_id: requestId
            };
            
            setChats(prevChats => prevChats.map(chat => {
              if (chat.id === chatId) {
                // Check if message already exists
                const hasCompletionMsg = chat.messages.some(m => 
                  m.content.includes('Dataset sampling completed') && m.request_id === requestId
                );
                if (hasCompletionMsg) return chat;
                
                return {
                  ...chat,
                  messages: [...chat.messages, completionMessage],
                };
              }
              return chat;
            }));
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
        clearInterval(pollInterval);
      }
    }, 2000); // Poll every 2 seconds
    
    // Stop after 5 minutes
    setTimeout(() => clearInterval(pollInterval), 300000);
  };

  const currentChat = chats.find(c => c.id === activeChat);

  if (loadingChats) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 size={32} className="animate-spin text-slate-600" />
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Chat History Sidebar */}
      <div className="w-64 border-r border-slate-800 bg-slate-950/50 flex flex-col">
        <div className="p-3 border-b border-slate-800">
          <button
            onClick={createNewChat}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus size={16} />
            New Chat
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {chats.map(chat => (
            <div
              key={chat.id}
              className={`group flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors ${
                activeChat === chat.id
                  ? 'bg-slate-800 text-white'
                  : 'hover:bg-slate-800/50 text-slate-400'
              }`}
              onClick={() => setActiveChat(chat.id)}
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <MessageSquare size={14} />
                <span className="text-xs truncate">{chat.title}</span>
              </div>
              {chats.length > 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteChat(chat.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 rounded transition-opacity"
                >
                  <Trash2 size={12} className="text-red-400" />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!currentChat || !currentChat.messages || currentChat.messages.length === 0 ? (
            <div className="h-full flex items-center justify-center text-slate-500">
              <div className="text-center">
                <MessageSquare size={48} className="mx-auto mb-4 opacity-50" />
                <p className="text-sm">Start a conversation to plan your dataset</p>
                <p className="text-xs mt-2">Describe what kind of dataset you need</p>
              </div>
            </div>
          ) : (
            currentChat.messages.map(message => (
              <div key={message.id}>
                <div
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-3 ${
                      message.role === 'user'
                        ? 'bg-cyan-600 text-white'
                        : 'bg-slate-800 text-slate-100'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    <div className="flex items-center gap-1 mt-2 text-xs opacity-70">
                      <Clock size={10} />
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
                
                {/* Plan Confirmation UI */}
                {message.plan && message.role === 'assistant' && (
                  <div className="flex justify-start mt-3">
                    <div className="max-w-[80%] rounded-lg border-2 border-cyan-500/50 bg-slate-900/80 p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <CheckCircle size={20} className="text-cyan-400" />
                        <h4 className="font-semibold text-cyan-400">Dataset Plan Ready</h4>
                      </div>
                      
                      <div className="space-y-2 text-sm text-slate-300 mb-4">
                        <div className="flex justify-between">
                          <span className="text-slate-500">Query:</span>
                          <span className="font-medium">{message.plan.query}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Type:</span>
                          <span className="font-medium capitalize">{message.plan.data_type}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Total Items:</span>
                          <span className="font-medium">{message.plan.total_items}</span>
                        </div>
                        <div className="flex flex-col gap-1">
                          <span className="text-slate-500">Classes:</span>
                          <div className="flex flex-wrap gap-1">
                            {message.plan.classes.map((cls, idx) => (
                              <span key={idx} className="px-2 py-0.5 bg-slate-800 rounded text-xs border border-slate-700">
                                {cls}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                      
                      <button
                        onClick={() => executePlan(message.plan!)}
                        disabled={executingPlan}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                      >
                        {executingPlan ? (
                          <>
                            <Loader2 size={16} className="animate-spin" />
                            Executing...
                          </>
                        ) : (
                          <>
                            <CheckCircle size={16} />
                            Execute Plan
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                )}
                
                {/* Sampling Status */}
                {message.request_id && samplingStatus[message.request_id] && (
                  <div className="flex justify-start mt-3">
                    <div className="max-w-[80%] rounded-lg border border-blue-500/50 bg-slate-900/80 p-4">
                      <div className="flex items-center gap-2 mb-3">
                        {samplingStatus[message.request_id].status === 'completed' ? (
                          <CheckCircle size={16} className="text-emerald-400" />
                        ) : (
                          <Loader2 size={16} className="animate-spin text-blue-400" />
                        )}
                        <h4 className={`font-semibold ${samplingStatus[message.request_id].status === 'completed' ? 'text-emerald-400' : 'text-blue-400'}`}>
                          {samplingStatus[message.request_id].status === 'completed' ? 'Sampling Complete' : 'Sampling in Progress'}
                        </h4>
                      </div>
                      
                      <div className="space-y-3">
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-400">Progress:</span>
                          <span className="text-white font-medium">
                            {samplingStatus[message.request_id].progress} / {samplingStatus[message.request_id].total}
                          </span>
                        </div>
                        
                        <div className="w-full bg-slate-800 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full transition-all duration-300 ${
                              samplingStatus[message.request_id].status === 'completed' ? 'bg-emerald-500' : 'bg-blue-500'
                            }`}
                            style={{ 
                              width: `${(samplingStatus[message.request_id].progress / samplingStatus[message.request_id].total) * 100}%` 
                            }}
                          />
                        </div>
                        
                        {samplingStatus[message.request_id].status === 'completed' && (
                          <>
                            {samplingStatus[message.request_id].samples && samplingStatus[message.request_id].samples!.length > 0 && (
                              <div className="pt-2 border-t border-slate-700">
                                <p className="text-xs text-slate-400 mb-2">Sample URLs:</p>
                                <div className="space-y-1">
                                  {samplingStatus[message.request_id].samples!.slice(0, 3).map((sample: any, idx: number) => (
                                    <a
                                      key={idx}
                                      href={sample.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="block text-xs text-cyan-400 hover:text-cyan-300 truncate"
                                    >
                                      {sample.url}
                                    </a>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            <div className="pt-2 space-y-2">
                              <p className="text-sm text-slate-300">
                                ✅ {samplingStatus[message.request_id].progress} samples sourced and ready
                              </p>
                              <button
                                onClick={async () => {
                                  try {
                                    const res = await fetch('/api/start-full-run', {
                                      method: 'POST',
                                      headers: { 'Content-Type': 'application/json' },
                                      body: JSON.stringify({
                                        request_id: message.request_id,
                                        persist: true
                                      })
                                    });
                                    if (res.ok) {
                                      const data = await res.json();
                                      const successMsg: Message = {
                                        id: `msg-${Date.now()}-${++messageIdCounter.current}`,
                                        role: 'assistant',
                                        content: `✅ Full download started!\n\nRequest ID: ${data.request_id}\n\nThe dataset will be downloaded to your filesystem. Check the Datasets tab after completion.`,
                                        timestamp: new Date().toISOString(),
                                      };
                                      setChats(prevChats => prevChats.map(chat => {
                                        if (chat.id === activeChat) {
                                          return { ...chat, messages: [...chat.messages, successMsg] };
                                        }
                                        return chat;
                                      }));
                                    } else {
                                      alert('❌ Failed to start full download. Please try again.');
                                    }
                                  } catch (error) {
                                    console.error('Failed to start full download:', error);
                                    alert('❌ Error starting full download.');
                                  }
                                }}
                                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium transition-colors"
                              >
                                <Download size={16} />
                                Start Full Download
                              </button>
                              <p className="text-xs text-slate-500 text-center">
                                This will download all samples to your filesystem
                              </p>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-800 text-slate-100 rounded-lg p-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-slate-800 p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !isLoading && sendMessage()}
              placeholder="Describe your dataset needs..."
              className="flex-1 px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
