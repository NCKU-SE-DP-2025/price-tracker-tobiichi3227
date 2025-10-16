<template>
    <nav class="navbar" ref="navbar">
        <div class="title">
            <RouterLink to="/overview">價格追蹤小幫手</RouterLink>
        </div>
        <button class="navbar-button" id="navbar-toggle" @click="toggleNavbar">
            <span class="navbar-toggler-icon" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect y="4" width="24" height="2" rx="1" fill="#333"/>
                    <rect y="11" width="24" height="2" rx="1" fill="#333"/>
                    <rect y="18" width="24" height="2" rx="1" fill="#333"/>
                </svg>
            </span>
        </button>
        <ul class="navbar-links" :class="{ active: isNavbarOpen }" id="navbar-links">
            <li><RouterLink to="/overview" @click="toggleNavbar">物價概覽</RouterLink></li>
            <li><RouterLink to="/trending" @click="toggleNavbar">物價趨勢</RouterLink></li>
            <li><RouterLink to="/news" @click="toggleNavbar">相關新聞</RouterLink></li>
            <li v-if="!isLoggedIn">
                <RouterLink to="/login" @click="toggleNavbar">登入</RouterLink>
            </li>
            <li v-else @click="logout">Hi, {{ getUserName }}! 登出</li>
        </ul>
    </nav>
</template>

<script>
import { ref, computed, watch, onBeforeUnmount } from 'vue';
import { useAuthStore } from '@/stores/auth';

const isNavbarOpen = ref(false);
const navbar = ref(null);
const isLoggedIn = computed(() => {
    const userStore = useAuthStore();
    return userStore.isLoggedIn;
});

const getUserName = computed(() => {
    const userStore = useAuthStore();
    return userStore.getUserName;
});

const logout = () => {
    const userStore = useAuthStore();
    userStore.logout();
    toggleNavbar();
};

const toggleNavbar = () => {
    isNavbarOpen.value = !isNavbarOpen.value;
};

const handleClickOutside = (event) => {
    if (navbar.value && !navbar.value.contains(event.target)) {
        isNavbarOpen.value = false;
    }
};

watch(isNavbarOpen, (newVal) => {
    if (newVal) {
        document.addEventListener('click', handleClickOutside);
    } else {
        document.removeEventListener('click', handleClickOutside);
    }
});

onBeforeUnmount(() => {
    document.removeEventListener('click', handleClickOutside);
});

export default {
    name: 'NavBar',
    setup() {
        return {
            navbar,
            isLoggedIn,
            getUserName,
            isNavbarOpen,
            logout,
            toggleNavbar,
        };
    },
};
</script>

<style scoped>
.navbar {
    display: flex;
    justify-content: space-between;
    background-color: #f3f3f3;
    padding: 1.5em;
    height: 4.5em;
    width: 100%;
    align-items: center;
    box-shadow: 0 0 5px #000000;
}

.navbar ul {
    list-style: none;
    justify-content: space-around;
}

.title > a {
    font-size: 1.4em;
    font-weight: bold;
    color: #2c3e50 !important;
}

.navbar li {
    color: #575b5d;
    margin: 0 0.5em;
    font-size: 1.2em;
}

.navbar li:hover {
    cursor: pointer;
    font-weight: bold;
}

.navbar a {
    text-decoration: none;
    color: #575b5d;
}

.navbar-button {
    display: none;
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
}

.navbar-links {
    display: flex;
    gap: 1rem;
}

:root {
    --z-navbar: 100;
}

@media (max-width: 768px) {
    .navbar-links {
        flex-direction: column;
        position: absolute;
        top: 56px;
        right: 0;
        background: #f8f9fa;
        width: 100%;
        display: none;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        z-index: var(--z-navbar);
    }
    .navbar-links.active {
        display: flex;
    }
    .navbar-button {
        display: block;
    }
}
</style>
