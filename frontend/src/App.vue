<template>
  <div class="min-h-screen bg-gray-100">
    <!-- Auth Screen -->
    <div v-if="!store.isAuthenticated" class="py-12">
      <AuthForm />
    </div>

    <!-- Main Dashboard -->
    <div v-else class="container mx-auto px-4 py-8">
      <!-- Instance Info -->
      <InstanceInfo />

      <!-- Search Filters -->
      <SearchFilters />

      <!-- Email List -->
      <EmailList @email-click="handleEmailClick" />

      <!-- Email Detail Modal -->
      <EmailDetail
        v-if="store.currentEmail"
        :email="store.currentEmail"
        @close="handleCloseEmail"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useAppStore } from './stores/appStore';
import AuthForm from './components/AuthForm.vue';
import InstanceInfo from './components/InstanceInfo.vue';
import SearchFilters from './components/SearchFilters.vue';
import EmailList from './components/EmailList.vue';
import EmailDetail from './components/EmailDetail.vue';

const store = useAppStore();

// Load instance on mount if secret exists
onMounted(async () => {
  if (store.secret) {
    await store.loadInstance();
    if (store.isAuthenticated) {
      await store.loadEmails();
    }
  }
});

async function handleEmailClick(emailId) {
  await store.loadEmailDetail(emailId);
}

function handleCloseEmail() {
  store.clearCurrentEmail();
}
</script>

<style>
/* Global styles */
html, body {
  margin: 0;
  padding: 0;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
</style>
