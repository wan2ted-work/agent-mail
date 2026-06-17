<template>
  <div class="mb-6">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-lg font-semibold text-gray-900">
        Custom Domains
      </h3>
      <button
        class="px-3 py-1 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
        @click="showAdd = !showAdd"
      >
        + Add Domain
      </button>
    </div>

    <p class="text-xs text-gray-500 mb-3">
      Use your own domain. All mail sent to <strong>anything@yourdomain.com</strong>
      lands in this space once the domain is verified (its MX points to us).
    </p>

    <!-- Add Domain Form -->
    <div
      v-if="showAdd"
      class="bg-gray-50 rounded-lg p-4 mb-4"
    >
      <form
        class="flex gap-2"
        @submit.prevent="handleAdd"
      >
        <input
          v-model="newDomain"
          type="text"
          placeholder="acme.com"
          class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          required
        >
        <button
          type="submit"
          :disabled="store.loading.mutation"
          class="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors disabled:opacity-50"
        >
          Add
        </button>
        <button
          type="button"
          class="px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-700 rounded-lg transition-colors"
          @click="showAdd = false; newDomain = ''"
        >
          Cancel
        </button>
      </form>
    </div>

    <!-- Domains List -->
    <div
      v-if="store.instanceDomains.length > 0"
      class="space-y-3"
    >
      <div
        v-for="d in store.instanceDomains"
        :key="d.id"
        class="bg-gray-50 rounded-lg p-4"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <code class="text-sm font-mono font-semibold text-gray-900">{{ d.domain }}</code>
            <span
              :class="[
                'px-2 py-0.5 rounded-full text-xs font-medium',
                d.is_verified ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
              ]"
            >
              {{ d.is_verified ? 'Verified' : 'Pending verification' }}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <button
              v-if="!d.is_verified"
              :disabled="store.loading.mutation"
              class="px-3 py-1 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors disabled:opacity-50"
              @click="handleVerify(d.domain)"
            >
              Verify
            </button>
            <button
              :disabled="store.loading.mutation"
              class="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
              @click="handleRemove(d.domain)"
            >
              Remove
            </button>
          </div>
        </div>

        <!-- DNS instructions for pending domains -->
        <div
          v-if="!d.is_verified"
          class="mt-3 bg-yellow-50 border border-yellow-200 rounded p-3"
        >
          <p class="text-xs text-yellow-800 mb-2">
            Add this <strong>MX record</strong> at your DNS provider, then click <strong>Verify</strong>:
          </p>
          <div class="grid grid-cols-[auto,1fr] gap-x-3 gap-y-1 text-xs font-mono bg-white rounded p-2">
            <span class="text-gray-500">Type</span><span class="text-gray-900">MX</span>
            <span class="text-gray-500">Name/Host</span><span class="text-gray-900">{{ d.domain }} (or @)</span>
            <span class="text-gray-500">Value</span><span class="text-gray-900">{{ mailHost }}</span>
            <span class="text-gray-500">Priority</span><span class="text-gray-900">10</span>
          </div>
          <p
            v-if="pendingMessage[d.domain]"
            class="text-xs text-yellow-700 mt-2"
          >
            {{ pendingMessage[d.domain] }}
          </p>
        </div>

        <p
          v-else
          class="text-xs text-gray-500 mt-2"
        >
          Receiving mail at <strong>anything@{{ d.domain }}</strong>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useAppStore } from '../stores/appStore';
import { MAIL_HOST } from '../config';

const store = useAppStore();
const showAdd = ref(false);
const newDomain = ref('');
const mailHost = MAIL_HOST;
const pendingMessage = ref({});

async function handleAdd() {
  const domain = newDomain.value.trim().toLowerCase();
  if (!domain) return;
  try {
    await store.addDomain(domain);
    newDomain.value = '';
    showAdd.value = false;
  } catch {
    // error surfaced via store.error
  }
}

async function handleVerify(domain) {
  try {
    const res = await store.verifyDomain(domain);
    if (res && !res.is_verified) {
      pendingMessage.value = { ...pendingMessage.value, [domain]: res.message || 'MX not pointing to us yet.' };
    } else {
      pendingMessage.value = { ...pendingMessage.value, [domain]: '' };
    }
  } catch {
    // error surfaced via store.error
  }
}

async function handleRemove(domain) {
  if (!confirm(`Remove domain "${domain}"?`)) return;
  try {
    await store.removeDomain(domain);
  } catch {
    // error surfaced via store.error
  }
}
</script>
