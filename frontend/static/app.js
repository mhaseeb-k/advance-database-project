/**
 * PulseNet - Social Media App JS
 * Features: Auth, SPA Routing, Feed, Profiles, Admin, OCC Versioning
 */

const API_BASE = "/api";
let currentUser = null;
let currentToken = localStorage.getItem("pulseToken");
let currentFeedFilter = "trending";
let feedSkip = 0;
const FEED_LIMIT = 10;
let profileSkip = 0;
let otherProfileSkip = 0;
let viewedUserId = null;

// --- INITIALIZATION ---
document.addEventListener("DOMContentLoaded", () => {
    initParticles();
    if (currentToken) {
        checkAuth();
    } else {
        showScreen("auth-screen");
    }

    // Modal close listeners
    window.onclick = (event) => {
        if (event.target.classList.contains("modal-overlay")) {
            closePostModal();
            closeEditProfileModal();
            closeCommentsModal();
        }
    };

    // Textarea counter
    const postTextarea = document.getElementById("post-content");
    const charCounter = document.getElementById("char-count");
    postTextarea?.addEventListener("input", () => {
        charCounter.textContent = postTextarea.value.length;
    });
});

// --- AUTH FUNCTIONS ---
async function checkAuth() {
    try {
        const res = await fetch(`${API_BASE}/users/me`, {
            headers: { "Authorization": `Bearer ${currentToken}` }
        });
        if (res.ok) {
            currentUser = await res.json();
            onLoginSuccess();
        } else {
            logout();
        }
    } catch (err) {
        console.error("Auth check failed", err);
        logout();
    }
}

function onLoginSuccess() {
    showScreen("main-screen");
    updateSidebar();
    showPage("feed");
    if (currentUser.is_admin) {
        document.getElementById("nav-admin").style.display = "flex";
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById("login-username").value;
    const password = document.getElementById("login-password").value;
    const errorEl = document.getElementById("login-error");
    const btn = document.getElementById("login-btn");

    setLoading(btn, true);
    errorEl.classList.add("hidden");

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (res.ok) {
            currentToken = data.access_token;
            currentUser = data.user;
            localStorage.setItem("pulseToken", currentToken);
            onLoginSuccess();
            showToast("Welcome back, " + currentUser.username);
        } else {
            errorEl.textContent = data.detail || "Login failed";
            errorEl.classList.remove("hidden");
        }
    } catch (err) {
        errorEl.textContent = "Connection error";
        errorEl.classList.remove("hidden");
    } finally {
        setLoading(btn, false);
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById("reg-username").value;
    const email = document.getElementById("reg-email").value;
    const password = document.getElementById("reg-password").value;
    const errorEl = document.getElementById("register-error");
    const btn = document.getElementById("register-btn");

    setLoading(btn, true);
    errorEl.classList.add("hidden");

    try {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, email, password })
        });
        const data = await res.json();
        if (res.ok) {
            currentToken = data.access_token;
            currentUser = data.user;
            localStorage.setItem("pulseToken", currentToken);
            onLoginSuccess();
            showToast("Account created successfully!");
        } else {
            errorEl.textContent = data.detail || "Registration failed";
            errorEl.classList.remove("hidden");
        }
    } catch (err) {
        errorEl.textContent = "Connection error";
        errorEl.classList.remove("hidden");
    } finally {
        setLoading(btn, false);
    }
}

function logout() {
    currentToken = null;
    currentUser = null;
    localStorage.removeItem("pulseToken");
    showScreen("auth-screen");
}

function handleLogout() {
    logout();
    showToast("Logged out safely");
}

// --- NAVIGATION ---
function showScreen(screenId) {
    document.querySelectorAll(".screen").forEach(s => s.classList.add("hidden"));
    document.getElementById(screenId).classList.remove("hidden");
    document.getElementById(screenId).classList.add("active");
}

function showPage(pageId) {
    document.querySelectorAll(".page").forEach(p => p.classList.add("hidden"));
    document.getElementById(`page-${pageId}`).classList.remove("hidden");
    document.getElementById(`page-${pageId}`).classList.add("active");
    
    document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
    const navItem = document.getElementById(`nav-${pageId}`);
    if (navItem) navItem.classList.add("active");

    if (pageId === "feed") loadFeed(true);
    if (pageId === "profile") loadProfile();
    if (pageId === "admin") loadAdminDashboard();

    // Close mobile nav if open
    document.getElementById("sidebar").classList.remove("open");
}

function switchAuthTab(tab) {
    document.querySelectorAll(".auth-tab").forEach(t => t.classList.remove("active"));
    document.getElementById(`tab-${tab}`).classList.add("active");
    if (tab === 'login') {
        document.getElementById("login-form").classList.remove("hidden");
        document.getElementById("register-form").classList.add("hidden");
    } else {
        document.getElementById("login-form").classList.add("hidden");
        document.getElementById("register-form").classList.remove("hidden");
    }
}

// --- FEED LOGIC ---
async function setFeedFilter(filter) {
    currentFeedFilter = filter;
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    document.getElementById(`filter-${filter === 'trending' ? 'trending' : filter === 'recent' ? 'recent' : 'top'}`).classList.add("active");
    loadFeed(true);
}

async function loadFeed(reset = false) {
    if (reset) {
        feedSkip = 0;
        document.getElementById("feed-posts").innerHTML = '<div class="loader-container"><div class="spinner"></div></div>';
    }
    
    const endpoint = currentFeedFilter === "trending" ? "trending" : currentFeedFilter === "recent" ? "recent" : "top-liked";
    try {
        const res = await fetch(`${API_BASE}/feed/${endpoint}?skip=${feedSkip}&limit=${FEED_LIMIT}`);
        const posts = await res.json();
        
        if (reset) document.getElementById("feed-posts").innerHTML = "";
        
        if (posts.length === 0 && reset) {
            document.getElementById("feed-posts").innerHTML = '<div class="empty-state"><h3>No posts yet</h3><p>Be the first to share something!</p></div>';
            document.getElementById("feed-load-more").style.display = "none";
            return;
        }

        posts.forEach(post => {
            const card = createPostCard(post);
            document.getElementById("feed-posts").appendChild(card);
        });

        document.getElementById("feed-load-more").style.display = posts.length < FEED_LIMIT ? "none" : "block";
    } catch (err) {
        showToast("Error loading feed", "error");
    }
}

function loadMoreFeed() {
    feedSkip += FEED_LIMIT;
    loadFeed(false);
}

// --- PROFILE LOGIC ---
async function loadProfile() {
    try {
        const res = await fetch(`${API_BASE}/users/me`, {
            headers: { "Authorization": `Bearer ${currentToken}` }
        });
        currentUser = await res.json();
        renderProfileInfo(currentUser);
        loadProfilePosts(true);
    } catch (err) {
        showToast("Error loading profile", "error");
    }
}

function renderProfileInfo(user, isOther = false) {
    const prefix = isOther ? "other-profile" : "profile";
    document.getElementById(`${prefix}-username`).textContent = user.username;
    if (!isOther) document.getElementById(`${prefix}-email`).textContent = user.email;
    document.getElementById(`${prefix}-joined`).textContent = `Joined ${new Date(user.joined_at).toLocaleDateString()}`;
    document.getElementById(`${prefix}-posts`).textContent = user.stats.post_count;
    document.getElementById(`${prefix}-followers`).textContent = user.stats.follower_count;
    
    const avatar = document.getElementById(isOther ? "other-profile-avatar" : "profile-avatar-large");
    avatar.textContent = user.username[0].toUpperCase();
}

async function loadProfilePosts(reset = false) {
    if (reset) {
        profileSkip = 0;
        document.getElementById("profile-posts-list").innerHTML = '<div class="loader-container"><div class="spinner"></div></div>';
    }
    
    try {
        const res = await fetch(`${API_BASE}/users/${currentUser.id}/posts?skip=${profileSkip}&limit=${FEED_LIMIT}`);
        const posts = await res.json();
        
        if (reset) document.getElementById("profile-posts-list").innerHTML = "";
        
        posts.forEach(post => {
            const card = createPostCard(post);
            document.getElementById("profile-posts-list").appendChild(card);
        });

        document.getElementById("profile-load-more").style.display = posts.length < FEED_LIMIT ? "none" : "block";
    } catch (err) {
        showToast("Error loading posts", "error");
    }
}

async function showUserProfile(userId) {
    if (userId === currentUser.id) {
        showPage("profile");
        return;
    }
    
    viewedUserId = userId;
    showPage("user-profile");
    document.getElementById("other-profile-posts-list").innerHTML = '<div class="loader-container"><div class="spinner"></div></div>';
    
    try {
        const res = await fetch(`${API_BASE}/users/${userId}`);
        const user = await res.json();
        renderProfileInfo(user, true);
        loadOtherUserPosts(true);
    } catch (err) {
        showToast("Error loading user profile", "error");
    }
}

async function loadOtherUserPosts(reset = false) {
    if (reset) otherProfileSkip = 0;
    try {
        const res = await fetch(`${API_BASE}/users/${viewedUserId}/posts?skip=${otherProfileSkip}&limit=${FEED_LIMIT}`);
        const posts = await res.json();
        if (reset) document.getElementById("other-profile-posts-list").innerHTML = "";
        posts.forEach(post => {
            const card = createPostCard(post);
            document.getElementById("other-profile-posts-list").appendChild(card);
        });
        document.getElementById("other-profile-load-more").style.display = posts.length < FEED_LIMIT ? "none" : "block";
    } catch (err) {}
}

// --- POSTS & COMMENTS ---
function createPostCard(post) {
    const div = document.createElement("div");
    div.className = "post-card";
    div.dataset.id = post.id;
    div.dataset.version = post.version;

    const isOwner = post.author.user_id === currentUser.id;
    const isAdmin = currentUser.is_admin;

    div.innerHTML = `
        <div class="post-header">
            <div class="post-author" onclick="showUserProfile('${post.author.user_id}')">
                <div class="post-author-avatar">${post.author.username[0].toUpperCase()}</div>
                <div class="post-author-info">
                    <div class="author-name">${post.author.username}</div>
                    <div class="post-time">${formatDate(post.timestamp)}</div>
                </div>
            </div>
            <div class="post-actions-menu">
                ${isOwner || isAdmin ? `
                    <button class="btn-icon" onclick="openEditPost('${post.id}')"><svg viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
                    <button class="btn-icon" onclick="deletePost('${post.id}')"><svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg></button>
                ` : ''}
            </div>
        </div>
        <div class="post-content">${post.content}</div>
        <div class="post-footer">
            <div class="post-metrics">
                <button class="metric-btn" onclick="likePost('${post.id}')">
                    <svg viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg>
                    <span class="count">${post.metrics.likes}</span>
                </button>
                <button class="metric-btn" onclick="openComments('${post.id}')">
                    <svg viewBox="0 0 24 24"><path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/></svg>
                    <span class="count">${post.metrics.comment_count}</span>
                </button>
            </div>
            ${post.metrics.likes + post.metrics.comment_count * 2 > 100 ? '<span class="trending-badge">🔥 Trending</span>' : ''}
        </div>
    `;
    return div;
}

let editingPostId = null;
function openPostModal() {
    editingPostId = null;
    document.getElementById("post-modal-title").textContent = "New Post";
    document.getElementById("post-btn-text").textContent = "Publish";
    document.getElementById("post-content").value = "";
    document.getElementById("post-modal").classList.remove("hidden");
}

async function openEditPost(postId) {
    editingPostId = postId;
    try {
        const res = await fetch(`${API_BASE}/posts/${postId}`);
        const post = await res.json();
        document.getElementById("post-modal-title").textContent = "Edit Post";
        document.getElementById("post-btn-text").textContent = "Save Changes";
        document.getElementById("post-content").value = post.content;
        document.getElementById("post-modal").classList.remove("hidden");
        document.getElementById("post-modal").dataset.version = post.version;
    } catch (err) {}
}

function closePostModal() {
    document.getElementById("post-modal").classList.add("hidden");
}

async function submitPost(e) {
    e.preventDefault();
    const content = document.getElementById("post-content").value;
    const btn = document.getElementById("post-submit-btn");
    const errorEl = document.getElementById("post-error");
    
    setLoading(btn, true);
    errorEl.classList.add("hidden");

    try {
        let res;
        if (editingPostId) {
            const version = parseInt(document.getElementById("post-modal").dataset.version);
            res = await fetch(`${API_BASE}/posts/${editingPostId}`, {
                method: "PATCH",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${currentToken}`
                },
                body: JSON.stringify({ content, version })
            });
        } else {
            res = await fetch(`${API_BASE}/posts/`, {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${currentToken}`
                },
                body: JSON.stringify({ content })
            });
        }
        
        if (res.ok) {
            showToast(editingPostId ? "Post updated" : "Post published");
            closePostModal();
            if (document.getElementById("page-feed").classList.contains("active")) loadFeed(true);
            else if (document.getElementById("page-profile").classList.contains("active")) loadProfile();
        } else {
            const data = await res.json();
            errorEl.textContent = data.detail || "Operation failed";
            errorEl.classList.remove("hidden");
        }
    } catch (err) {
        errorEl.textContent = "Request failed";
        errorEl.classList.remove("hidden");
    } finally {
        setLoading(btn, false);
    }
}

async function deletePost(postId) {
    if (!confirm("Are you sure you want to delete this post?")) return;
    try {
        const res = await fetch(`${API_BASE}/posts/${postId}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${currentToken}` }
        });
        if (res.ok) {
            showToast("Post deleted");
            const card = document.querySelector(`.post-card[data-id="${postId}"]`);
            if (card) card.remove();
        }
    } catch (err) {}
}

async function likePost(postId) {
    try {
        const res = await fetch(`${API_BASE}/posts/${postId}/like`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${currentToken}` }
        });
        if (res.ok) {
            const btn = document.querySelector(`.post-card[data-id="${postId}"] .metric-btn:first-child`);
            btn.classList.add("liked");
            const count = btn.querySelector(".count");
            count.textContent = parseInt(count.textContent) + 1;
        } else if (res.status === 409) {
            showToast("Syncing... try again", "warn");
        }
    } catch (err) {}
}

// --- COMMENTS LOGIC ---
let activePostId = null;
async function openComments(postId) {
    activePostId = postId;
    document.getElementById("comments-modal").classList.remove("hidden");
    document.getElementById("comments-list").innerHTML = '<div class="loader-container"><div class="spinner"></div></div>';
    
    try {
        // Load post preview
        const pRes = await fetch(`${API_BASE}/posts/${postId}`);
        const post = await pRes.json();
        document.getElementById("comments-post-preview").textContent = post.content;

        // Load comments
        const cRes = await fetch(`${API_BASE}/comments/post/${postId}`);
        const comments = await cRes.json();
        renderComments(comments);
    } catch (err) {}
}

function renderComments(comments) {
    const list = document.getElementById("comments-list");
    list.innerHTML = "";
    if (comments.length === 0) {
        list.innerHTML = '<p class="empty-state">No comments yet. Be the first!</p>';
        return;
    }
    comments.forEach(c => {
        const div = document.createElement("div");
        div.className = "comment-item";
        const isOwner = c.user_id === currentUser.id || currentUser.is_admin;
        div.innerHTML = `
            <div class="comment-avatar">${c.username[0].toUpperCase()}</div>
            <div class="comment-body">
                <div class="comment-author">${c.username}</div>
                <div class="comment-text">${c.text}</div>
                <div class="comment-time">${formatDate(c.timestamp)}</div>
                ${isOwner ? `
                    <div class="comment-actions">
                        <button class="btn-ghost btn-sm" onclick="deleteComment('${c.id}')">Delete</button>
                    </div>
                ` : ''}
            </div>
        `;
        list.appendChild(div);
    });
}

async function submitComment(e) {
    e.preventDefault();
    const input = document.getElementById("comment-input");
    const text = input.value;
    if (!text.trim()) return;

    try {
        const res = await fetch(`${API_BASE}/comments/`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Authorization": `Bearer ${currentToken}`
            },
            body: JSON.stringify({ post_id: activePostId, text })
        });
        if (res.ok) {
            input.value = "";
            openComments(activePostId);
            // Update count in feed if visible
            const feedCount = document.querySelector(`.post-card[data-id="${activePostId}"] .metric-btn:nth-child(2) .count`);
            if (feedCount) feedCount.textContent = parseInt(feedCount.textContent) + 1;
        }
    } catch (err) {}
}

async function deleteComment(commentId) {
    if (!confirm("Delete this comment?")) return;
    try {
        const res = await fetch(`${API_BASE}/comments/${commentId}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${currentToken}` }
        });
        if (res.ok) {
            openComments(activePostId);
            const feedCount = document.querySelector(`.post-card[data-id="${activePostId}"] .metric-btn:nth-child(2) .count`);
            if (feedCount) feedCount.textContent = Math.max(0, parseInt(feedCount.textContent) - 1);
        }
    } catch (err) {}
}

function closeCommentsModal() {
    document.getElementById("comments-modal").classList.add("hidden");
}

// --- PROFILE EDIT ---
function openEditProfileModal() {
    document.getElementById("edit-email").value = currentUser.email;
    document.getElementById("edit-password").value = "";
    document.getElementById("edit-profile-version").textContent = currentUser.version;
    document.getElementById("edit-profile-modal").classList.remove("hidden");
}

function closeEditProfileModal() {
    document.getElementById("edit-profile-modal").classList.add("hidden");
}

async function submitEditProfile(e) {
    e.preventDefault();
    const email = document.getElementById("edit-email").value;
    const password = document.getElementById("edit-password").value;
    const version = parseInt(document.getElementById("edit-profile-version").textContent);
    const errorEl = document.getElementById("edit-profile-error");

    const body = { version };
    if (email && email !== currentUser.email) body.email = email;
    if (password) body.password = password;

    if (Object.keys(body).length === 1) {
        closeEditProfileModal();
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/users/me`, {
            method: "PATCH",
            headers: { 
                "Content-Type": "application/json",
                "Authorization": `Bearer ${currentToken}`
            },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        if (res.ok) {
            currentUser = data;
            showToast("Profile updated");
            renderProfileInfo(currentUser);
            closeEditProfileModal();
        } else {
            errorEl.textContent = data.detail || "Update failed";
            errorEl.classList.remove("hidden");
        }
    } catch (err) {
        errorEl.textContent = "Request failed";
        errorEl.classList.remove("hidden");
    }
}

// --- ADMIN PANEL ---
let currentAdminTab = "users";
async function loadAdminDashboard() {
    try {
        const res = await fetch(`${API_BASE}/admin/stats`, {
            headers: { "Authorization": `Bearer ${currentToken}` }
        });
        const stats = await res.json();
        const statsRow = document.getElementById("admin-stats-row");
        statsRow.innerHTML = `
            <div class="admin-stat-card"><span class="admin-stat-value">${stats.total_users}</span><span class="admin-stat-label">Users</span></div>
            <div class="admin-stat-card"><span class="admin-stat-value">${stats.total_posts}</span><span class="admin-stat-label">Posts</span></div>
            <div class="admin-stat-card"><span class="admin-stat-value">${stats.total_comments}</span><span class="admin-stat-label">Comments</span></div>
        `;
        switchAdminTab(currentAdminTab);
    } catch (err) {}
}

async function switchAdminTab(tab) {
    currentAdminTab = tab;
    document.querySelectorAll(".admin-tab").forEach(t => t.classList.remove("active"));
    document.getElementById(`atab-${tab}`).classList.add("active");
    
    const container = document.getElementById("admin-content");
    container.innerHTML = '<div class="loader-container"><div class="spinner"></div></div>';

    try {
        const res = await fetch(`${API_BASE}/admin/${tab}`, {
            headers: { "Authorization": `Bearer ${currentToken}` }
        });
        const items = await res.json();
        container.innerHTML = "";
        
        if (items.length === 0) {
            container.innerHTML = '<p class="empty-state">No items found</p>';
            return;
        }

        items.forEach(item => {
            const row = document.createElement("div");
            row.className = "admin-row";
            
            let title = "", sub = "", id = item.id;
            if (tab === "users") {
                title = item.username;
                sub = item.email;
            } else if (tab === "posts") {
                title = item.author.username;
                sub = item.content.substring(0, 50) + "...";
            } else {
                title = item.username;
                sub = item.text;
            }

            row.innerHTML = `
                <div class="admin-row-info">
                    <div class="admin-row-title">${title} <span class="occ-badge">v${item.version}</span></div>
                    <div class="admin-row-sub">${sub}</div>
                </div>
                <div class="admin-row-actions">
                    <button class="btn btn-danger btn-sm" onclick="adminDelete('${tab}', '${id}')">Delete</button>
                </div>
            `;
            container.appendChild(row);
        });
    } catch (err) {}
}

async function adminDelete(type, id) {
    if (!confirm(`Permanently delete this ${type}?`)) return;
    try {
        const res = await fetch(`${API_BASE}/admin/${type}/${id}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${currentToken}` }
        });
        if (res.ok) {
            showToast(`${type} deleted by admin`);
            switchAdminTab(currentAdminTab);
        }
    } catch (err) {}
}

// --- HELPERS ---
function showToast(msg, type = "success") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type === 'error' ? 'error' : type === 'warn' ? 'warn' : ''}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

function setLoading(btn, isLoading) {
    const text = btn.querySelector(".btn-text");
    const loader = btn.querySelector(".btn-loader");
    if (isLoading) {
        btn.disabled = true;
        text.classList.add("hidden");
        loader.classList.remove("hidden");
    } else {
        btn.disabled = false;
        text.classList.remove("hidden");
        loader.classList.add("hidden");
    }
}

function updateSidebar() {
    document.getElementById("sidebar-username").textContent = currentUser.username;
    document.getElementById("sidebar-role").textContent = currentUser.is_admin ? "Administrator" : "Member";
    document.getElementById("sidebar-avatar").textContent = currentUser.username[0].toUpperCase();
    document.getElementById("feed-avatar").textContent = currentUser.username[0].toUpperCase();
}

function toggleMobileNav() {
    document.getElementById("sidebar").classList.toggle("open");
}

function formatDate(dateStr) {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = (now - d) / 1000;
    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
    return d.toLocaleDateString();
}

function initParticles() {
    const container = document.getElementById("particles");
    if (!container) return;
    for (let i = 0; i < 30; i++) {
        const p = document.createElement("div");
        p.className = "particle";
        const size = Math.random() * 4 + 2;
        p.style.width = `${size}px`;
        p.style.height = `${size}px`;
        p.style.left = `${Math.random() * 100}%`;
        p.style.animationDuration = `${Math.random() * 5 + 5}s`;
        p.style.animationDelay = `${Math.random() * 10}s`;
        container.appendChild(p);
    }
}
