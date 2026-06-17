import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { instanceApi, emailApi } from '../services/api';

export const useAppStore = defineStore('app', () => {
  // State
  const secret = ref(localStorage.getItem('secret') || '');
  const instance = ref(null);
  const emails = ref([]);
  const currentEmail = ref(null);
  const loading = ref(false);
  const error = ref(null);

  // Pagination
  const emailsPagination = ref({
    total: 0,
    skip: 0,
    limit: 20,
  });

  // Filters
  const filters = ref({
    from_email: '',
    nickname: '',
    subject: '',
    extracted_key: '',
  });

  // Computed
  const isAuthenticated = computed(() => !!secret.value && !!instance.value);
  const hasEmails = computed(() => emails.value.length > 0);
  const instanceKeys = computed(() => instance.value?.keys || []);
  const instanceDomains = computed(() => instance.value?.domains || []);

  // Actions
  async function setSecret(newSecret) {
    secret.value = newSecret;
    localStorage.setItem('secret', newSecret);
    await loadInstance();
  }

  function clearSecret() {
    secret.value = '';
    instance.value = null;
    emails.value = [];
    currentEmail.value = null;
    localStorage.removeItem('secret');
  }

  async function loadInstance() {
    if (!secret.value) return;

    loading.value = true;
    error.value = null;

    try {
      const response = await instanceApi.get(secret.value);
      instance.value = response.data;
    } catch (err) {
      error.value = err.response?.data?.error || 'Failed to load instance';
      console.error('Error loading instance:', err);
      clearSecret();
    } finally {
      loading.value = false;
    }
  }

  // DEPRECATED: instances are now created automatically on GET request
  // async function createInstance(data) {
  //   loading.value = true;
  //   error.value = null;
  //
  //   try {
  //     const response = await instanceApi.create(data);
  //     const newInstance = response.data;
  //     await setSecret(newInstance.id);
  //     return newInstance;
  //   } catch (err) {
  //     error.value = err.response?.data?.error || 'Failed to create instance';
  //     console.error('Error creating instance:', err);
  //     throw err;
  //   } finally {
  //     loading.value = false;
  //   }
  // }

  async function updateInstance(data) {
    if (!secret.value) return;

    loading.value = true;
    error.value = null;

    try {
      const response = await instanceApi.update(secret.value, data);
      instance.value = response.data;
    } catch (err) {
      error.value = err.response?.data?.error || 'Failed to update instance';
      console.error('Error updating instance:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function loadEmails(resetPagination = false) {
    if (!secret.value) return;

    if (resetPagination) {
      emailsPagination.value.skip = 0;
    }

    loading.value = true;
    error.value = null;

    try {
      const params = {
        skip: emailsPagination.value.skip,
        limit: emailsPagination.value.limit,
        ...Object.fromEntries(
          Object.entries(filters.value).filter(([_, v]) => v !== '')
        ),
      };

      const response = await emailApi.getList(secret.value, params);
      emails.value = response.data.items;
      emailsPagination.value.total = response.data.total;
    } catch (err) {
      error.value = err.response?.data?.error || 'Failed to load emails';
      console.error('Error loading emails:', err);
    } finally {
      loading.value = false;
    }
  }

  async function loadEmailDetail(emailId) {
    if (!secret.value) return;

    loading.value = true;
    error.value = null;

    try {
      const response = await emailApi.getDetail(secret.value, emailId);
      currentEmail.value = response.data;
    } catch (err) {
      error.value = err.response?.data?.error || 'Failed to load email';
      console.error('Error loading email detail:', err);
    } finally {
      loading.value = false;
    }
  }

  function setFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters };
  }

  function clearFilters() {
    filters.value = {
      from_email: '',
      nickname: '',
      subject: '',
      extracted_key: '',
    };
  }

  async function addKey(key) {
    if (!secret.value) return;

    loading.value = true;
    error.value = null;

    try {
      await instanceApi.addKey(secret.value, key);
      await loadInstance(); // Reload to get updated keys
    } catch (err) {
      error.value = err.response?.data?.error || 'Failed to add key';
      console.error('Error adding key:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function removeKey(key) {
    if (!secret.value) return;

    loading.value = true;
    error.value = null;

    try {
      await instanceApi.removeKey(secret.value, key);
      await loadInstance(); // Reload to get updated keys
    } catch (err) {
      error.value = err.response?.data?.error || 'Failed to remove key';
      console.error('Error removing key:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  }

  function nextPage() {
    if (emailsPagination.value.skip + emailsPagination.value.limit < emailsPagination.value.total) {
      emailsPagination.value.skip += emailsPagination.value.limit;
      loadEmails();
    }
  }

  function prevPage() {
    if (emailsPagination.value.skip > 0) {
      emailsPagination.value.skip = Math.max(0, emailsPagination.value.skip - emailsPagination.value.limit);
      loadEmails();
    }
  }

  function clearCurrentEmail() {
    currentEmail.value = null;
  }

  // Custom domains
  async function addDomain(domain) {
    if (!secret.value) return;
    loading.value = true;
    error.value = null;
    try {
      const response = await instanceApi.addDomain(secret.value, domain);
      await loadInstance(); // refresh domains list
      return response.data; // includes dns_record (MX) to display
    } catch (err) {
      error.value = err.response?.data?.error || 'Failed to add domain';
      console.error('Error adding domain:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function verifyDomain(domain) {
    if (!secret.value) return;
    loading.value = true;
    error.value = null;
    try {
      const response = await instanceApi.verifyDomain(secret.value, domain);
      await loadInstance();
      return response.data; // is_verified true/false (+ message when pending)
    } catch (err) {
      error.value = err.response?.data?.error || 'Failed to verify domain';
      console.error('Error verifying domain:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function removeDomain(domain) {
    if (!secret.value) return;
    loading.value = true;
    error.value = null;
    try {
      await instanceApi.removeDomain(secret.value, domain);
      await loadInstance();
    } catch (err) {
      error.value = err.response?.data?.error || 'Failed to remove domain';
      console.error('Error removing domain:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  }

  return {
    // State
    secret,
    instance,
    emails,
    currentEmail,
    loading,
    error,
    emailsPagination,
    filters,

    // Computed
    isAuthenticated,
    hasEmails,
    instanceKeys,
    instanceDomains,

    // Actions
    setSecret,
    clearSecret,
    loadInstance,
    // createInstance, // DEPRECATED
    updateInstance,
    loadEmails,
    loadEmailDetail,
    setFilters,
    clearFilters,
    addKey,
    removeKey,
    addDomain,
    verifyDomain,
    removeDomain,
    nextPage,
    prevPage,
    clearCurrentEmail,
  };
});
