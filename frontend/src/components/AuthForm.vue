<template>
  <div class="max-w-2xl mx-auto p-6">
    <div class="bg-white rounded-lg shadow-lg p-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-2 text-center">
        {{ APP_NAME }}
      </h1>
      <p class="text-center text-gray-600 mb-8">
        {{ APP_TAGLINE }}
      </p>

      <!-- Login Form -->
      <form
        class="space-y-4"
        @submit.prevent="handleLogin"
      >
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
          <p class="text-sm text-blue-800">
            <strong>Note:</strong> Enter any UUID to connect. If the instance doesn't exist,
            it will be created automatically.
          </p>
        </div>

        <div>
          <label
            for="secret"
            class="block text-sm font-medium text-gray-700 mb-2"
          >
            Secret (UUID)
          </label>
          <input
            id="secret"
            v-model="loginSecret"
            type="text"
            placeholder="550e8400-e29b-41d4-a716-446655440000"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          >
          <p class="mt-1 text-sm text-gray-500">
            Enter your instance secret to connect or create new instance
          </p>
        </div>

        <button
          type="submit"
          :disabled="store.loading.instance"
          class="w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ store.loading.instance ? 'Connecting...' : 'Connect' }}
        </button>
      </form>

      <!-- Error Message -->
      <div
        v-if="store.error"
        class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg"
      >
        <p class="text-red-600 text-sm">
          {{ store.error }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useAppStore } from '../stores/appStore';
import { APP_NAME, APP_TAGLINE } from '../config';

const store = useAppStore();
const loginSecret = ref('');

async function handleLogin() {
  if (!loginSecret.value.trim()) return;
  await store.setSecret(loginSecret.value.trim());
}
</script>
