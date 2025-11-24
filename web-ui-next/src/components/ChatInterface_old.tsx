"use client";

import { useState, useRef, useEffect } from 'react';
import { Send, Plus, MessageSquare, Trash2, Clock, CheckCircle, Loader2 } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  plan?: DatasetPlan;
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
  createdAt: Date;
}

interface ChatInterfaceProps {
  onPlanGenerated?: (plan: any) => void;
}

export function ChatInterface({ onPlanGenerated }: ChatInterfaceProps) {
  const [chats, setChats] = useState<Chat[]>([
    {
      id: '1',
      title: 'New Dataset Plan',
      messages: [],
      createdAt: new Date(),
    }
  ]);
  const [activeChat, setActiveChat] = useState<string>('1');
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [executingPlan, setExecutingPlan] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chats]);

  const createNewChat = () => {
    const newChat: Chat = {
      id: Date.now().toString(),
      title: `Chat ${chats.length + 1}`,
      messages: [],
      createdAt: new Date(),
    };
    setChats([...chats, newChat]);
    setActiveChat(newChat.id);
  };

  const deleteChat = (chatId: string) => {
    if (chats.length === 1) return;
    const filtered = chats.filter(c => c.id !== chatId);
    setChats(filtered);
    if (activeChat === chatId) {
      setActiveChat(filtered[0].id);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    const currentChat = chats.find(c => c.id === activeChat);
    if (!currentChat) return;

    const updatedChats = chats.map(chat => {
      if (chat.id === activeChat) {
        return {
          ...chat,
          messages: [...chat.messages, userMessage],
          title: chat.messages.length === 0 ? input.slice(0, 30) : chat.title,
        };
      }
      return chat;
    });

    setChats(updatedChats);
    setInput('');
    setIsLoading(true);

    try {
      // Build conversation history for API
      const conversationHistory = currentChat.messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      // Call chat API
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_history: conversationHistory
        })
      });

      if (!res.ok) {
        throw new Error('Chat API failed');
      }

      const data = await res.json();
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        plan: data.plan || undefined
      };

      setChats(chats.map(chat => {
        if (chat.id === activeChat) {
          return {
            ...chat,
            messages: [...chat.messages, userMessage, assistantMessage],
          };
        }
        return chat;
      }));
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      };
      
      setChats(chats.map(chat => {
        if (chat.id === activeChat) {
          return {
            ...chat,
            messages: [...chat.messages, userMessage, errorMessage],
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
      
      // Add success message to chat
      const successMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `✅ Plan executed successfully! Created dataset with ${result.samples?.length || 0} samples. You can view it in the Build Tool or Datasets section.`,
        timestamp: new Date(),
      };

      setChats(chats.map(chat => {
        if (chat.id === activeChat) {
          return {
            ...chat,
            messages: [...chat.messages, successMessage],
          };
        }
        return chat;
      }));

      // Notify parent if callback provided
      if (onPlanGenerated) {
        onPlanGenerated(result);
      }
    } catch (error) {
      console.error('Execute plan error:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: '❌ Failed to execute plan. Please try again or use the Build Tool manually.',
        timestamp: new Date(),
      };
      
      setChats(chats.map(chat => {
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

  const currentChat = chats.find(c => c.id === activeChat);

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
          {currentChat?.messages.length === 0 ? (
            <div className="h-full flex items-center justify-center text-slate-500">
              <div className="text-center">
                <MessageSquare size={48} className="mx-auto mb-4 opacity-50" />
                <p className="text-sm">Start a conversation to plan your dataset</p>
                <p className="text-xs mt-2">Describe what kind of dataset you need</p>
              </div>
            </div>
          ) : (
            currentChat?.messages.map(message => (
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
                      {message.timestamp.toLocaleTimeString()}
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
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Describe your dataset needs..."
              className="flex-1 px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
