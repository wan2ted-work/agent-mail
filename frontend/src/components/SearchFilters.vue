<template>
  <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
    <h3 class="text-lg font-semibold text-gray-900 mb-4">
      Search & Filter
    </h3>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div>
        <label
          for="from-email"
          class="block text-sm font-medium text-gray-700 mb-2"
        >
          From Email
        </label>
        <input
          id="from-email"
          v-model="localFilters.from_email"
          type="text"
          placeholder="sender@example.com"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
      </div>

      <div>
        <label
          for="nickname"
          class="block text-sm font-medium text-gray-700 mb-2"
        >
          Nickname (Recipient)
        </label>
        <input
          id="nickname"
          v-model="localFilters.nickname"
          type="text"
          placeholder="username"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
        <p class="text-xs text-gray-500 mt-1">
          Part before @ in recipient address
        </p>
      </div>

      <div>
        <label
          for="subject"
          class="block text-sm font-medium text-gray-700 mb-2"
        >
          Subject
        </label>
        <input
          id="subject"
          v-model="localFilters.subject"
          type="text"
          placeholder="Search in subject..."
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
      </div>

      <div>
        <label
          for="extracted-key"
          class="block text-sm font-medium text-gray-700 mb-2"
        >
          Key (Domain)
        </label>
        <input
          id="extracted-key"
          v-model="localFilters.extracted_key"
          type="text"
          placeholder="key"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
        <p class="text-xs text-gray-500 mt-1">
          Filter by instance key
        </p>
      </div>
    </div>

    <div class="flex gap-3 mt-4">
      <button
        class="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white font-medium rounded-lg transition-colors"
        @click="handleSearch"
      >
        Search
      </button>
      <button
        class="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-medium rounded-lg transition-colors"
        @click="handleClear"
      >
        Clear
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useAppStore, EMPTY_FILTERS } from '../stores/appStore';

const store = useAppStore();

// Local draft of the filters; only applied to the store on Search (button-driven).
const localFilters = ref({ ...store.filters });

// Keep the draft in sync if the store filters change elsewhere (e.g. Clear).
watch(() => store.filters, (newFilters) => {
  localFilters.value = { ...newFilters };
}, { deep: true });

function handleSearch() {
  store.setFilters(localFilters.value);
  store.loadEmails(true);
}

function handleClear() {
  localFilters.value = { ...EMPTY_FILTERS };
  store.clearFilters();
  store.loadEmails(true);
}
</script>
