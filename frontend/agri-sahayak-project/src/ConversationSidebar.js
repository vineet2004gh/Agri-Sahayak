import React, { useEffect, useState } from "react";
import axios from "axios";
import { useTranslation } from "react-i18next";
import {
  Plus,
  Search,
  MessageSquare,
  Clock,
  User,
  Settings,
  LogOut,
  Trash2,
  Edit3,
  MoreHorizontal,
} from "lucide-react";

const ConversationSidebar = ({
  userId,
  selectedConversationId,
  onSelect,
  onLogout,
  collapsed = false,
  onSearchIconClick,
}) => {
  const { t } = useTranslation();
  const [conversations, setConversations] = useState([]);
  const [allConversations, setAllConversations] = useState([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [showUserMenu, setShowUserMenu] = useState(false);

  // New state for delete and rename functionality
  const [editingConversationId, setEditingConversationId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [showActionsMenu, setShowActionsMenu] = useState(null);

  useEffect(() => {
    if (!userId) return;

    // Fetch user profile
    const fetchUserProfile = async () => {
      try {
        const res = await axios.get(`http://127.0.0.1:8000/users/${userId}`);
        setUserProfile(res?.data?.user);
      } catch (e) {
        console.error("Failed to fetch user profile:", e);
      }
    };

    const fetchConversations = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await axios.get(
          `http://127.0.0.1:8000/users/${userId}/conversations`
        );
        const list = res?.data?.conversations || [];
        setAllConversations(list);
        setConversations(list);
      } catch (e) {
        setError(t("failedToLoadConversations"));
      } finally {
        setIsLoading(false);
      }
    };

    fetchUserProfile();
    fetchConversations();
  }, [userId, t]);

  // Debounced search
  useEffect(() => {
    const id = setTimeout(() => {
      const q = (query || "").toLowerCase();
      if (!q) {
        setConversations(allConversations);
        return;
      }
      setConversations(
        allConversations.filter((c) =>
          (c.title || "").toLowerCase().includes(q)
        )
      );
    }, 200);
    return () => clearTimeout(id);
  }, [query, allConversations]);

  // Close actions menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showActionsMenu && !event.target.closest(".actions-menu")) {
        setShowActionsMenu(null);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showActionsMenu]);

  const formatDate = (timestamp) => {
    if (!timestamp) return "";
    const date = new Date(timestamp);
    const now = new Date();
    const diffInHours = (now - date) / (1000 * 60 * 60);

    if (diffInHours < 24) {
      return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    } else if (diffInHours < 168) {
      // 7 days
      return date.toLocaleDateString([], { weekday: "short" });
    } else {
      return date.toLocaleDateString([], { month: "short", day: "numeric" });
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post("http://127.0.0.1:8000/logout", {
        user_id: userId,
      });
    } catch (_) {}
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_name");
    onLogout?.();
  };

  // New functions for delete and rename
  const handleDeleteConversation = async (conversationId) => {
    if (!window.confirm(t("deleteConfirm"))) return;

    try {
      await axios.delete(
        `http://127.0.0.1:8000/conversations/${conversationId}`
      );

      // Remove from local state
      setConversations((prev) =>
        prev.filter((c) => c.conversation_id !== conversationId)
      );
      setAllConversations((prev) =>
        prev.filter((c) => c.conversation_id !== conversationId)
      );

      // If this was the selected conversation, clear selection
      if (selectedConversationId === conversationId) {
        onSelect?.(null);
      }

      setShowActionsMenu(null);
    } catch (error) {
      console.error("Failed to delete conversation:", error);
      window.alert("Failed to delete conversation. Please try again.");
    }
  };

  const handleRenameConversation = async (conversationId, newTitle) => {
    if (!newTitle.trim()) return;

    try {
      await axios.patch(
        `http://127.0.0.1:8000/conversations/${conversationId}`,
        {
          title: newTitle.trim(),
        }
      );

      // Update local state
      setConversations((prev) =>
        prev.map((c) =>
          c.conversation_id === conversationId
            ? { ...c, title: newTitle.trim() }
            : c
        )
      );
      setAllConversations((prev) =>
        prev.map((c) =>
          c.conversation_id === conversationId
            ? { ...c, title: newTitle.trim() }
            : c
        )
      );

      setEditingConversationId(null);
      setEditingTitle("");
      setShowActionsMenu(null);
    } catch (error) {
      console.error("Failed to rename conversation:", error);
      window.alert("Failed to rename conversation. Please try again.");
    }
  };

  const startEditing = (conversation) => {
    setEditingConversationId(conversation.conversation_id);
    setEditingTitle(conversation.title || "");
    setShowActionsMenu(null);
  };

  const cancelEditing = () => {
    setEditingConversationId(null);
    setEditingTitle("");
  };

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 overflow-x-hidden">
      {/* Header with New Chat button */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-800">
        <button
          onClick={() => onSelect(null)}
          className="w-full flex items-center gap-3 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl transition-colors font-medium text-sm"
        >
          <Plus size={18} />
          New Chat
        </button>
      </div>

      {/* Search */}
      {!collapsed ? (
        <div className="relative mb-4 px-2">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="Search conversations..."
            className="w-full pl-10 pr-3 py-2.5 rounded-2xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-800 dark:text-gray-200 placeholder-gray-500 dark:placeholder-gray-400 transition-all duration-200"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      ) : (
        <div className="px-2 mb-4 flex justify-center">
          <button
            type="button"
            onClick={() => onSearchIconClick?.()}
            title={t('search') || 'Search'}
            aria-label={t('search') || 'Search'}
            className="p-2.5 rounded-full text-gray-600 hover:text-blue-600 dark:text-gray-300 dark:hover:text-blue-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <Search size={18} />
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center py-8">
          <div className="flex items-center gap-2">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
              <div
                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                style={{ animationDelay: "0.1s" }}
              ></div>
              <div
                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                style={{ animationDelay: "0.2s" }}
              ></div>
            </div>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Loading...
            </span>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="text-sm text-red-600 dark:text-red-400 mb-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-2xl mx-2">
          {error}
        </div>
      )}

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden space-y-1 px-2 custom-scrollbar scroll-smooth">
        {conversations.map((c) => {
          const isActive = c.conversation_id === selectedConversationId;
          const isEditing = editingConversationId === c.conversation_id;

          return (
            <div
              key={c.conversation_id}
              className={`relative group rounded-2xl border transition-all duration-200 ${
                isActive
                  ? "bg-blue-100 dark:bg-blue-900/40 border-blue-400 dark:border-blue-500 shadow-lg ring-2 ring-blue-400 dark:ring-blue-500 text-blue-900 dark:text-blue-100 font-bold"
                  : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              {isEditing ? (
                // Edit mode
                <div className="p-3">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          handleRenameConversation(
                            c.conversation_id,
                            editingTitle
                          );
                        } else if (e.key === "Escape") {
                          cancelEditing();
                        }
                      }}
                      className="flex-1 bg-transparent border-none outline-none text-sm font-medium text-gray-900 dark:text-gray-100"
                      placeholder={t("enterTitle")}
                      autoFocus
                    />
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() =>
                          handleRenameConversation(
                            c.conversation_id,
                            editingTitle
                          )
                        }
                        className="p-1 text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300"
                        title={t("save")}
                      >
                        ✓
                      </button>
                      <button
                        onClick={cancelEditing}
                        className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                        title={t("cancel")}
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                // Normal mode
                <div className="flex items-center">
                  <button
                    className={`flex-1 text-left p-3 transition-all duration-200 ${
                      isActive
                        ? "text-blue-900 dark:text-blue-100"
                        : "text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100"
                    }`}
                    onClick={() => onSelect?.(c.conversation_id)}
                    title={c.title || t("untitledConversation")}
                  >
                    <div className="flex items-start gap-3">
                      <MessageSquare
                        size={16}
                        className={`flex-shrink-0 mt-0.5 ${
                          isActive
                            ? "text-blue-600 dark:text-blue-400"
                            : "text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300"
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <div
                          className={`font-medium text-sm ${
                            isActive
                              ? "text-blue-900 dark:text-blue-100"
                              : "text-gray-900 dark:text-gray-100"
                          }`}
                          style={{
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            maxWidth: "180px",
                            display: "block",
                          }}
                          title={c.title || t("untitledConversation")}
                        >
                          {c.title && c.title.length > 40
                            ? c.title.slice(0, 40) + "..."
                            : c.title || t("untitledConversation")}
                        </div>
                        {c.timestamp && (
                          <div className="flex items-center gap-1 mt-1">
                            <Clock size={12} className="text-gray-400" />
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              {formatDate(c.timestamp)}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </button>

                  {/* Actions Menu */}
                  <div className="relative">
                    <button
                      onClick={() =>
                        setShowActionsMenu(
                          showActionsMenu === c.conversation_id
                            ? null
                            : c.conversation_id
                        )
                      }
                      className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 opacity-0 group-hover:opacity-100 transition-all duration-200"
                      title={t("moreActions")}
                    >
                      <MoreHorizontal size={16} />
                    </button>

                    {showActionsMenu === c.conversation_id && (
                      <div className="actions-menu absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg z-10 min-w-[140px]">
                        <button
                          onClick={() => startEditing(c)}
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        >
                          <Edit3 size={14} />
                          Rename
                        </button>
                        <button
                          onClick={() =>
                            handleDeleteConversation(c.conversation_id)
                          }
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                        >
                          <Trash2 size={14} />
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {conversations.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <MessageSquare
              size={48}
              className="text-gray-300 dark:text-gray-600 mb-3"
            />
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
              {t("noConversationsYet")}
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Start a new conversation to get advice
            </p>
          </div>
        )}
      </div>

      {/* User Profile Section */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-3 mt-4">
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="w-full flex items-center gap-3 p-2 rounded-2xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-all duration-200"
          >
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
              <User size={16} className="text-white" />
            </div>
            <div className="flex-1 text-left">
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                {userProfile?.name ||
                  localStorage.getItem("user_name") ||
                  t("farmer")}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {userProfile?.email || "vnjain2004@gmail.com"}
              </div>
            </div>
          </button>

          {/* User Menu Dropdown */}
          {showUserMenu && (
            <div className="absolute bottom-full left-0 right-0 mb-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-lg z-10">
              <div className="p-2">
                <button
                  onClick={() => setShowUserMenu(false)}
                  className="w-full flex items-center gap-3 p-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-200 text-sm text-gray-700 dark:text-gray-300"
                >
                  <Settings size={16} />
                  <span>Settings</span>
                </button>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 p-2 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 transition-all duration-200 text-sm text-red-600 dark:text-red-400"
                >
                  <LogOut size={16} />
                  <span>{t("logout")}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ConversationSidebar;
