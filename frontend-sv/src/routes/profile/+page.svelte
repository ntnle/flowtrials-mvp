<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { Input } from "$lib/components/ui/input/index.js";
  import { Card, CardHeader, CardTitle, CardContent } from "$lib/components/ui/card/index.js";
  import { user } from '$lib/authStore';
  import {
    getUserProfile,
    updateUserProfile,
    getUserParticipationRequests,
    withdrawParticipationRequest,
    isResearcher,
    getUserStudies,
    createDraftStudy,
    updateStudy,
    deleteStudy,
    uploadStudyMedia,
    deleteStudyMedia,
    getPublicMediaUrl,
    getStudyParticipationRequests,
    updateParticipationRequestStatus,
    resetParticipationConsent,
    getTaskSubmissionsForStudy,
    getAudioRecordingUrl
  } from '$lib/supabase';

  let activeTab = 'requests'; // 'requests', 'studies', or 'info'
  let loading = true;
  let saveLoading = false;
  let uploadingMedia = false;
  let uploadError = '';
  let requests = [];
  let showSuccessMessage = false;
  let isUserResearcher = false;
  let userStudies = [];
  let showCreateForm = false;
  let editingStudyId = null;

  // Participation management state (researcher view)
  let selectedStudyForRequests = null;
  let studyParticipationRequests = [];
  let loadingRequests = false;

  // Task submissions state (researcher view)
  let selectedStudyForSubmissions = null;
  let studyTaskSubmissions = [];
  let loadingSubmissions = false;
  let expandedSubmissionId = null;
  let audioUrls = {}; // Cache for audio signed URLs
  let profile = {
    age: '',
    gender: '',
    race: '',
    ethnicity: '',
    conditions: [],
    other_condition: '',
    medications: '',
    allergies: '',
    previous_trials: '',
    trial_experience: '',
    zip_code: '',
    travel_radius: 25,
    weekday_availability: false,
    weekend_availability: false,
    preferred_time_of_day: '',
    in_person_willing: false,
    remote_willing: false,
    compensation_importance: 3,
    smoker: '',
    alcohol_use: '',
    exercise_frequency: '',
    has_insurance: '',
    insurance_type: '',
    additional_notes: ''
  };

  const conditionOptions = [
    'Diabetes', 'Asthma', 'Depression', 'Anxiety', 'Hypertension',
    'Cancer', 'Heart Disease', 'Arthritis', 'COPD', 'Other'
  ];

  // Study form state
  let studyForm = {
    title: '',
    source: '',
    brief_summary: '',
    detailed_description: '',
    eligibility_criteria: '',
    recruiting_status: 'RECRUITING',
    study_type: 'INTERVENTIONAL',
    conditions: [],
    interventions: [],
    locations: [],
    contacts: [],
    site_zips: [],
    media: [],
    tasks: []
  };

  // Task editor state
  let editingTaskIndex = null;
  let editingPageIndex = null;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    // Check if redirected from participation success
    if ($page.url.searchParams.get('participationSuccess') === 'true') {
      showSuccessMessage = true;
      goto('/profile', { replaceState: true, keepfocus: true, noScroll: true });
      // Hide message after 5 seconds
      setTimeout(() => {
        showSuccessMessage = false;
      }, 5000);
    }

    await loadData();
  });

  async function loadData() {
    loading = true;
    try {
      // Check if user is a researcher
      isUserResearcher = await isResearcher();

      // Set default tab based on researcher status
      if (isUserResearcher && activeTab === 'requests') {
        activeTab = 'studies';
      }

      // Load participation requests
      requests = await getUserParticipationRequests();

      // Load user studies if researcher
      if (isUserResearcher) {
        userStudies = await getUserStudies();
      }

      // Load profile data
      const profileData = await getUserProfile($user.id);
      if (profileData) {
        profile = { ...profile, ...profileData };
      }
    } catch (err) {
      console.error('Error loading profile data:', err);
    } finally {
      loading = false;
    }
  }

  async function handleWithdraw(requestId) {
    if (!confirm('Are you sure you want to withdraw this participation request?')) {
      return;
    }

    try {
      await withdrawParticipationRequest(requestId);
      // Reload requests
      requests = await getUserParticipationRequests();
    } catch (err) {
      alert('Failed to withdraw request. Please try again.');
    }
  }

  function toggleCondition(condition) {
    if (profile.conditions.includes(condition)) {
      profile.conditions = profile.conditions.filter(c => c !== condition);
    } else {
      profile.conditions = [...profile.conditions, condition];
    }
  }

  async function saveProfile() {
    saveLoading = true;
    try {
      await updateUserProfile($user.id, profile);
      alert('Profile saved successfully!');
    } catch (err) {
      alert('Failed to save profile. Please try again.');
    } finally {
      saveLoading = false;
    }
  }

  function getStatusColor(status) {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'approved': return 'bg-green-100 text-green-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      case 'withdrawn': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  }

  // Study management functions
  function resetStudyForm() {
    studyForm = {
      title: '',
      source: '',
      brief_summary: '',
      detailed_description: '',
      eligibility_criteria: '',
      recruiting_status: 'RECRUITING',
      study_type: 'INTERVENTIONAL',
      conditions: [],
      interventions: [],
      locations: [],
      contacts: [],
      site_zips: [],
      media: [],
      tasks: []
    };
    editingStudyId = null;
    editingTaskIndex = null;
    editingPageIndex = null;
  }

  function startEditStudy(study) {
    studyForm = {
      title: study.title || '',
      source: study.source || '',
      brief_summary: study.brief_summary || '',
      detailed_description: study.detailed_description || '',
      eligibility_criteria: study.eligibility_criteria || '',
      recruiting_status: study.recruiting_status || 'RECRUITING',
      study_type: study.study_type || 'INTERVENTIONAL',
      conditions: study.conditions || [],
      interventions: study.interventions || [],
      locations: study.locations || [],
      contacts: study.contacts || [],
      site_zips: study.site_zips || [],
      media: study.media || [],
      tasks: study.tasks || []
    };
    editingStudyId = study.id;
    editingTaskIndex = null;
    editingPageIndex = null;
    showCreateForm = true;
  }

  async function handleCreateOrUpdateStudy() {
    if (!studyForm.title.trim() || !studyForm.source.trim()) {
      alert('Title and Source are required fields');
      return;
    }

    // Normalize conditions to lowercase
    const normalizedData = {
      ...studyForm,
      conditions: studyForm.conditions.map(c => c.toLowerCase().trim()),
      site_zips: studyForm.site_zips.map(z => z.trim())
    };

    try {
      if (editingStudyId) {
        await updateStudy(editingStudyId, normalizedData);
      } else {
        await createDraftStudy(normalizedData);
      }

      // Reload studies
      userStudies = await getUserStudies();
      showCreateForm = false;
      resetStudyForm();
    } catch (err) {
      console.error('Error saving study:', err);
      if (err.message?.includes('policy')) {
        alert('You do not have permission to create studies. Only researchers with .edu emails or allowlisted accounts can create studies.');
      } else {
        alert('Failed to save study. Please try again.');
      }
    }
  }

  async function handleDeleteStudy(studyId) {
    if (!confirm('Are you sure you want to delete this study? This action cannot be undone.')) {
      return;
    }

    try {
      await deleteStudy(studyId);
      userStudies = await getUserStudies();
    } catch (err) {
      console.error('Error deleting study:', err);
      alert('Failed to delete study. Please try again.');
    }
  }

  async function handleTogglePublish(study) {
    const action = study.is_published ? 'unpublish' : 'publish';
    if (!confirm(`Are you sure you want to ${action} this study?`)) {
      return;
    }

    try {
      await updateStudy(study.id, { is_published: !study.is_published });
      userStudies = await getUserStudies();
    } catch (err) {
      console.error('Error toggling publish status:', err);
      alert(`Failed to ${action} study. Please try again.`);
    }
  }

  function addConditionToStudy() {
    const input = prompt('Enter condition (e.g., diabetes, asthma):');
    if (input && input.trim()) {
      studyForm.conditions = [...studyForm.conditions, input.trim()];
    }
  }

  function removeConditionFromStudy(index) {
    studyForm.conditions = studyForm.conditions.filter((_, i) => i !== index);
  }

  function addZipToStudy() {
    const input = prompt('Enter ZIP code:');
    if (input && input.trim()) {
      studyForm.site_zips = [...studyForm.site_zips, input.trim()];
    }
  }

  function removeZipFromStudy(index) {
    studyForm.site_zips = studyForm.site_zips.filter((_, i) => i !== index);
  }

  // Task management functions
  function generateId() {
    return crypto.randomUUID();
  }

  function addTask() {
    const newTask = {
      id: generateId(),
      type: 'survey',
      title: 'New Survey',
      pages: [{
        id: generateId(),
        title: 'Page 1',
        blocks: []
      }]
    };
    studyForm.tasks = [...studyForm.tasks, newTask];
    editingTaskIndex = studyForm.tasks.length - 1;
    editingPageIndex = 0;
  }

  function removeTask(index) {
    if (!confirm('Delete this task? This cannot be undone.')) return;
    studyForm.tasks = studyForm.tasks.filter((_, i) => i !== index);
    if (editingTaskIndex === index) {
      editingTaskIndex = null;
      editingPageIndex = null;
    }
  }

  function addPage(taskIndex) {
    const newPage = {
      id: generateId(),
      title: `Page ${studyForm.tasks[taskIndex].pages.length + 1}`,
      blocks: []
    };
    studyForm.tasks[taskIndex].pages = [...studyForm.tasks[taskIndex].pages, newPage];
    studyForm.tasks = studyForm.tasks; // trigger reactivity
    editingPageIndex = studyForm.tasks[taskIndex].pages.length - 1;
  }

  function removePage(taskIndex, pageIndex) {
    if (studyForm.tasks[taskIndex].pages.length <= 1) {
      alert('A task must have at least one page');
      return;
    }
    if (!confirm('Delete this page? This cannot be undone.')) return;
    studyForm.tasks[taskIndex].pages = studyForm.tasks[taskIndex].pages.filter((_, i) => i !== pageIndex);
    studyForm.tasks = studyForm.tasks;
    if (editingPageIndex >= studyForm.tasks[taskIndex].pages.length) {
      editingPageIndex = studyForm.tasks[taskIndex].pages.length - 1;
    }
  }

  function addBlock(taskIndex, pageIndex, blockType) {
    const baseBlock = {
      id: generateId(),
      type: blockType
    };

    let newBlock;
    switch (blockType) {
      case 'text':
        newBlock = { ...baseBlock, content: 'Enter text here...' };
        break;
      case 'short_text':
        newBlock = { ...baseBlock, label: 'Question', required: false };
        break;
      case 'long_text':
        newBlock = { ...baseBlock, label: 'Question', required: false };
        break;
      case 'multiple_choice':
        newBlock = { ...baseBlock, label: 'Question', options: ['Option 1', 'Option 2'], required: false };
        break;
      case 'checkbox':
        newBlock = { ...baseBlock, label: 'Question', options: ['Option 1', 'Option 2'], required: false };
        break;
      case 'number':
        newBlock = { ...baseBlock, label: 'Question', required: false };
        break;
      case 'audio_recording':
        newBlock = { ...baseBlock, label: 'Record your response', required: false };
        break;
      default:
        newBlock = baseBlock;
    }

    studyForm.tasks[taskIndex].pages[pageIndex].blocks = [
      ...studyForm.tasks[taskIndex].pages[pageIndex].blocks,
      newBlock
    ];
    studyForm.tasks = studyForm.tasks;
  }

  function removeBlock(taskIndex, pageIndex, blockIndex) {
    studyForm.tasks[taskIndex].pages[pageIndex].blocks =
      studyForm.tasks[taskIndex].pages[pageIndex].blocks.filter((_, i) => i !== blockIndex);
    studyForm.tasks = studyForm.tasks;
  }

  function updateBlock(taskIndex, pageIndex, blockIndex, field, value) {
    studyForm.tasks[taskIndex].pages[pageIndex].blocks[blockIndex][field] = value;
    studyForm.tasks = studyForm.tasks;
  }

  function addOptionToBlock(taskIndex, pageIndex, blockIndex) {
    const block = studyForm.tasks[taskIndex].pages[pageIndex].blocks[blockIndex];
    block.options = [...(block.options || []), `Option ${(block.options?.length || 0) + 1}`];
    studyForm.tasks = studyForm.tasks;
  }

  function removeOptionFromBlock(taskIndex, pageIndex, blockIndex, optionIndex) {
    const block = studyForm.tasks[taskIndex].pages[pageIndex].blocks[blockIndex];
    block.options = block.options.filter((_, i) => i !== optionIndex);
    studyForm.tasks = studyForm.tasks;
  }

  function updateOption(taskIndex, pageIndex, blockIndex, optionIndex, value) {
    studyForm.tasks[taskIndex].pages[pageIndex].blocks[blockIndex].options[optionIndex] = value;
    studyForm.tasks = studyForm.tasks;
  }

  async function handleMediaFileSelect(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file count
    if (studyForm.media.length >= 10) {
      uploadError = 'Maximum 10 files allowed per study';
      setTimeout(() => uploadError = '', 3000);
      event.target.value = '';
      return;
    }

    // Validate file size (5MB)
    if (file.size > 5242880) {
      uploadError = 'File size must be under 5MB';
      setTimeout(() => uploadError = '', 3000);
      event.target.value = '';
      return;
    }

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/svg+xml', 'application/pdf'];
    if (!allowedTypes.includes(file.type)) {
      uploadError = 'Only images (JPEG, PNG, WebP, GIF, SVG) and PDFs are allowed';
      setTimeout(() => uploadError = '', 3000);
      event.target.value = '';
      return;
    }

    uploadingMedia = true;
    uploadError = '';

    try {
      // Need a temporary study ID for uploads during edit
      // For new studies, we'll upload after creation
      if (!editingStudyId) {
        uploadError = 'Please save the study first before uploading media';
        setTimeout(() => uploadError = '', 3000);
        event.target.value = '';
        return;
      }

      const path = await uploadStudyMedia(editingStudyId, file);
      const caption = prompt('Enter optional caption for this file:') || '';

      studyForm.media = [...studyForm.media, { path, caption: caption.trim() }];
      event.target.value = ''; // Reset input
    } catch (err) {
      console.error('Upload error:', err);
      uploadError = err.message || 'Failed to upload file';
      setTimeout(() => uploadError = '', 3000);
    } finally {
      uploadingMedia = false;
      event.target.value = '';
    }
  }

  async function removeMediaFromStudy(index) {
    const mediaItem = studyForm.media[index];

    if (!confirm('Delete this file? This cannot be undone.')) {
      return;
    }

    try {
      // Delete from storage
      if (mediaItem.path) {
        await deleteStudyMedia(mediaItem.path);
      }

      // Remove from form
      studyForm.media = studyForm.media.filter((_, i) => i !== index);
    } catch (err) {
      console.error('Delete error:', err);
      alert('Failed to delete file. Please try again.');
    }
  }

  // Researcher participation management functions
  async function loadStudyRequests(study) {
    selectedStudyForRequests = study;
    loadingRequests = true;
    try {
      studyParticipationRequests = await getStudyParticipationRequests(study.id);
    } catch (err) {
      console.error('Error loading participation requests:', err);
      studyParticipationRequests = [];
    } finally {
      loadingRequests = false;
    }
  }

  function closeRequestsView() {
    selectedStudyForRequests = null;
    studyParticipationRequests = [];
  }

  async function handleApproveRequest(requestId) {
    if (!confirm('Approve this participation request?')) return;
    try {
      await updateParticipationRequestStatus(requestId, 'approved');
      studyParticipationRequests = await getStudyParticipationRequests(selectedStudyForRequests.id);
    } catch (err) {
      console.error('Error approving request:', err);
      alert('Failed to approve request. Please try again.');
    }
  }

  async function handleRejectRequest(requestId) {
    if (!confirm('Reject this participation request?')) return;
    try {
      await updateParticipationRequestStatus(requestId, 'rejected');
      studyParticipationRequests = await getStudyParticipationRequests(selectedStudyForRequests.id);
    } catch (err) {
      console.error('Error rejecting request:', err);
      alert('Failed to reject request. Please try again.');
    }
  }

  async function handleResetConsent(requestId) {
    if (!confirm('Reset consent acknowledgment for this participant? They will need to re-acknowledge consent.')) return;
    try {
      await resetParticipationConsent(requestId);
      studyParticipationRequests = await getStudyParticipationRequests(selectedStudyForRequests.id);
    } catch (err) {
      console.error('Error resetting consent:', err);
      alert('Failed to reset consent. Please try again.');
    }
  }

  function getRequestStatusColor(status) {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'approved': return 'bg-green-100 text-green-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      case 'withdrawn': return 'bg-gray-100 text-gray-800';
      case 'contacted': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  }

  // Task submissions functions (researcher view)
  async function loadStudySubmissions(study) {
    selectedStudyForSubmissions = study;
    loadingSubmissions = true;
    expandedSubmissionId = null;
    try {
      studyTaskSubmissions = await getTaskSubmissionsForStudy(study.id);
    } catch (err) {
      console.error('Error loading task submissions:', err);
      studyTaskSubmissions = [];
    } finally {
      loadingSubmissions = false;
    }
  }

  function closeSubmissionsView() {
    selectedStudyForSubmissions = null;
    studyTaskSubmissions = [];
    expandedSubmissionId = null;
  }

  function toggleSubmissionExpand(submissionId) {
    expandedSubmissionId = expandedSubmissionId === submissionId ? null : submissionId;
  }

  function getTaskTitle(taskId) {
    if (!selectedStudyForSubmissions?.tasks) return taskId;
    const task = selectedStudyForSubmissions.tasks.find(t => t.id === taskId);
    return task?.title || taskId;
  }

  function getBlockLabel(taskId, blockId) {
    if (!selectedStudyForSubmissions?.tasks) return blockId;
    const task = selectedStudyForSubmissions.tasks.find(t => t.id === taskId);
    if (!task) return blockId;
    for (const page of task.pages || []) {
      const block = page.blocks?.find(b => b.id === blockId);
      if (block) return block.label || block.content || blockId;
    }
    return blockId;
  }

  function getBlockType(taskId, blockId) {
    if (!selectedStudyForSubmissions?.tasks) return null;
    const task = selectedStudyForSubmissions.tasks.find(t => t.id === taskId);
    if (!task) return null;
    for (const page of task.pages || []) {
      const block = page.blocks?.find(b => b.id === blockId);
      if (block) return block.type;
    }
    return null;
  }

  async function loadAudioUrl(path) {
    if (audioUrls[path]) return audioUrls[path];
    try {
      const url = await getAudioRecordingUrl(path);
      audioUrls[path] = url;
      audioUrls = audioUrls; // trigger reactivity
      return url;
    } catch (err) {
      console.error('Error loading audio URL:', err);
      return null;
    }
  }
</script>

<main class="min-h-screen bg-background p-6">
  <div class="mx-auto max-w-5xl">
    <h1 class="text-3xl font-bold mb-6">Manage Your Participation</h1>

    <!-- Success Message -->
    {#if showSuccessMessage}
      <div class="mb-6 p-4 bg-primary/10 text-primary rounded-md border border-primary/20">
        <div class="flex items-start gap-3">
          <svg class="w-5 h-5 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <div>
            <p class="font-medium">Request Submitted</p>
            <p class="text-sm mt-1 opacity-90">The study team will review your request and contact you if you're eligible. You can view your requests below.</p>
          </div>
        </div>
      </div>
    {/if}

    {#if loading}
      <div class="text-center py-12">
        <p class="text-muted-foreground">Loading...</p>
      </div>
    {:else}
      <!-- Tab Navigation -->
      <div class="border-b mb-6">
        <div class="flex gap-6">
          <button
            on:click={() => activeTab = 'studies'}
            class="pb-3 px-2 font-medium border-b-2 transition-colors {activeTab === 'studies' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'} {!isUserResearcher ? 'opacity-50' : ''}"
            title={!isUserResearcher ? 'Only researchers can manage studies' : ''}
          >
            My Studies ({userStudies.length})
          </button>
          <button
            on:click={() => activeTab = 'requests'}
            class="pb-3 px-2 font-medium border-b-2 transition-colors {activeTab === 'requests' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}"
          >
            Your Requests ({requests.length})
          </button>
          <button
            on:click={() => activeTab = 'info'}
            class="pb-3 px-2 font-medium border-b-2 transition-colors {activeTab === 'info' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}"
          >
            Personal Information
          </button>
        </div>
      </div>

      <!-- My Studies Tab -->
      {#if activeTab === 'studies'}
        <div class="space-y-4">
          {#if !isUserResearcher}
            <Card>
              <CardContent class="p-8 text-center">
                <p class="text-muted-foreground mb-2">Researcher access not enabled</p>
                <p class="text-sm text-muted-foreground">Only users with .edu email addresses or manually allowlisted accounts can create and manage studies.</p>
              </CardContent>
            </Card>
          {:else if showCreateForm}
            <!-- Create/Edit Study Form -->
            <Card>
              <CardHeader>
                <CardTitle>{editingStudyId ? 'Edit Study' : 'Create New Study'}</CardTitle>
              </CardHeader>
              <CardContent class="space-y-4">
                <div class="space-y-2">
                  <label for="study-title" class="text-sm font-medium">Title *</label>
                  <Input
                    id="study-title"
                    bind:value={studyForm.title}
                    placeholder="Study title"
                  />
                </div>

                <div class="space-y-2">
                  <label for="study-source" class="text-sm font-medium">Source * <span class="text-muted-foreground text-xs">(cannot be 'ctgov')</span></label>
                  <Input
                    id="study-source"
                    bind:value={studyForm.source}
                    placeholder="e.g., internal, stanford-med, etc."
                  />
                </div>

                <div class="space-y-2">
                  <label for="study-summary" class="text-sm font-medium">Brief Summary</label>
                  <textarea
                    id="study-summary"
                    bind:value={studyForm.brief_summary}
                    placeholder="Brief summary of the study"
                    rows="3"
                    class="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
                  ></textarea>
                </div>

                <div class="space-y-2">
                  <label for="study-description" class="text-sm font-medium">Detailed Description</label>
                  <textarea
                    id="study-description"
                    bind:value={studyForm.detailed_description}
                    placeholder="Detailed description"
                    rows="4"
                    class="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
                  ></textarea>
                </div>

                <div class="space-y-2">
                  <label for="study-eligibility" class="text-sm font-medium">Eligibility Criteria</label>
                  <textarea
                    id="study-eligibility"
                    bind:value={studyForm.eligibility_criteria}
                    placeholder="Eligibility criteria"
                    rows="4"
                    class="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
                  ></textarea>
                </div>

                <div class="grid grid-cols-2 gap-4">
                  <div class="space-y-2">
                    <label for="study-status" class="text-sm font-medium">Recruiting Status</label>
                    <select
                      id="study-status"
                      bind:value={studyForm.recruiting_status}
                      class="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
                    >
                      <option value="RECRUITING">Recruiting</option>
                      <option value="NOT_YET_RECRUITING">Not Yet Recruiting</option>
                      <option value="COMPLETED">Completed</option>
                      <option value="SUSPENDED">Suspended</option>
                    </select>
                  </div>

                  <div class="space-y-2">
                    <label for="study-type" class="text-sm font-medium">Study Type</label>
                    <select
                      id="study-type"
                      bind:value={studyForm.study_type}
                      class="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
                    >
                      <option value="INTERVENTIONAL">Interventional</option>
                      <option value="OBSERVATIONAL">Observational</option>
                    </select>
                  </div>
                </div>

                <div class="space-y-2">
                  <label class="text-sm font-medium">Conditions</label>
                  <div class="flex flex-wrap gap-2 mb-2">
                    {#each studyForm.conditions as condition, i}
                      <span class="px-2 py-1 bg-primary/10 text-primary text-sm rounded-md flex items-center gap-1">
                        {condition}
                        <button
                          type="button"
                          on:click={() => removeConditionFromStudy(i)}
                          class="text-primary hover:text-primary/70"
                        >×</button>
                      </span>
                    {/each}
                  </div>
                  <button
                    type="button"
                    on:click={addConditionToStudy}
                    class="text-sm px-3 py-1 border border-primary text-primary rounded-md hover:bg-primary/10"
                  >+ Add Condition</button>
                </div>

                <div class="space-y-2">
                  <label class="text-sm font-medium">Site ZIP Codes</label>
                  <div class="flex flex-wrap gap-2 mb-2">
                    {#each studyForm.site_zips as zip, i}
                      <span class="px-2 py-1 bg-primary/10 text-primary text-sm rounded-md flex items-center gap-1">
                        {zip}
                        <button
                          type="button"
                          on:click={() => removeZipFromStudy(i)}
                          class="text-primary hover:text-primary/70"
                        >×</button>
                      </span>
                    {/each}
                  </div>
                  <button
                    type="button"
                    on:click={addZipToStudy}
                    class="text-sm px-3 py-1 border border-primary text-primary rounded-md hover:bg-primary/10"
                  >+ Add ZIP</button>
                </div>

                <div class="space-y-2">
                  <label class="text-sm font-medium">Media (Supplemental Materials)</label>
                  <p class="text-xs text-muted-foreground mb-2">Upload posters, images (JPEG, PNG, WebP, GIF, SVG), or PDFs. Max 5MB per file, 10 files total.</p>

                  {#if !editingStudyId}
                    <p class="text-xs text-amber-600 bg-amber-50 dark:bg-amber-950/20 p-2 rounded border border-amber-200 dark:border-amber-900">
                      Note: Save the study first before uploading media files.
                    </p>
                  {/if}

                  {#if uploadError}
                    <div class="text-xs text-destructive bg-destructive/10 p-2 rounded">
                      {uploadError}
                    </div>
                  {/if}

                  <div class="grid grid-cols-2 gap-3 mb-2">
                    {#each studyForm.media as item, i}
                      <div class="relative border border-border rounded-md p-2 bg-muted/30">
                        <button
                          type="button"
                          on:click={() => removeMediaFromStudy(i)}
                          class="absolute top-1 right-1 w-6 h-6 bg-destructive text-destructive-foreground rounded-full text-xs font-bold hover:bg-destructive/90"
                        >×</button>

                        <div class="pr-7">
                          {#if item.path?.endsWith('.pdf')}
                            <div class="flex items-center gap-2 mb-1">
                              <svg class="w-8 h-8 text-muted-foreground" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                              </svg>
                              <span class="text-xs font-medium truncate">PDF</span>
                            </div>
                          {:else}
                            <img
                              src={getPublicMediaUrl(item.path)}
                              alt={item.caption || 'Study media'}
                              class="w-full h-24 object-cover rounded mb-1"
                            />
                          {/if}
                          {#if item.caption}
                            <p class="text-xs text-muted-foreground truncate">{item.caption}</p>
                          {:else}
                            <p class="text-xs text-muted-foreground italic">No caption</p>
                          {/if}
                        </div>
                      </div>
                    {/each}
                  </div>

                  {#if studyForm.media.length < 10}
                    <div class="flex items-center gap-2">
                      <label class="cursor-pointer">
                        <input
                          type="file"
                          accept="image/jpeg,image/png,image/webp,image/gif,image/svg+xml,application/pdf"
                          on:change={handleMediaFileSelect}
                          disabled={uploadingMedia || !editingStudyId}
                          class="hidden"
                        />
                        <span class="inline-block text-sm px-3 py-1.5 border border-primary text-primary rounded-md hover:bg-primary/10 {uploadingMedia || !editingStudyId ? 'opacity-50 cursor-not-allowed' : ''}">
                          {uploadingMedia ? 'Uploading...' : '+ Upload File'}
                        </span>
                      </label>
                      <span class="text-xs text-muted-foreground">
                        {studyForm.media.length}/10 files
                      </span>
                    </div>
                  {:else}
                    <p class="text-xs text-muted-foreground">Maximum 10 files reached</p>
                  {/if}
                </div>

                <!-- Tasks Section (only for editing existing studies) -->
                {#if editingStudyId}
                  <div class="space-y-4 pt-4 border-t border-border">
                    <div class="flex justify-between items-center">
                      <label class="text-sm font-medium">Study Tasks (Surveys)</label>
                      <button
                        type="button"
                        on:click={addTask}
                        class="text-sm px-3 py-1 border border-primary text-primary rounded-md hover:bg-primary/10"
                      >+ Add Survey Task</button>
                    </div>

                    {#if studyForm.tasks.length === 0}
                      <p class="text-xs text-muted-foreground bg-muted/50 p-3 rounded">
                        No tasks yet. Add a survey task for participants to complete after consent.
                      </p>
                    {:else}
                      <div class="space-y-3">
                        {#each studyForm.tasks as task, taskIndex}
                          <div class="border border-border rounded-md p-3 bg-muted/20">
                            <div class="flex justify-between items-start mb-2">
                              <div class="flex-1 mr-2">
                                <input
                                  type="text"
                                  bind:value={task.title}
                                  placeholder="Task title"
                                  class="w-full px-2 py-1 text-sm font-medium border border-input rounded bg-background"
                                />
                              </div>
                              <div class="flex gap-1">
                                <button
                                  type="button"
                                  on:click={() => { editingTaskIndex = editingTaskIndex === taskIndex ? null : taskIndex; editingPageIndex = 0; }}
                                  class="px-2 py-1 text-xs border rounded {editingTaskIndex === taskIndex ? 'bg-primary text-primary-foreground' : 'hover:bg-accent'}"
                                >{editingTaskIndex === taskIndex ? 'Close' : 'Edit'}</button>
                                <button
                                  type="button"
                                  on:click={() => removeTask(taskIndex)}
                                  class="px-2 py-1 text-xs border border-destructive text-destructive rounded hover:bg-destructive/10"
                                >Delete</button>
                              </div>
                            </div>

                            <div class="text-xs text-muted-foreground">
                              {task.pages?.length || 0} page(s), {task.pages?.reduce((sum, p) => sum + (p.blocks?.length || 0), 0) || 0} block(s)
                            </div>

                            <!-- Expanded task editor -->
                            {#if editingTaskIndex === taskIndex}
                              <div class="mt-3 pt-3 border-t border-border space-y-3">
                                <!-- Page tabs -->
                                <div class="flex gap-1 flex-wrap items-center">
                                  {#each task.pages as page, pageIndex}
                                    <button
                                      type="button"
                                      on:click={() => editingPageIndex = pageIndex}
                                      class="px-2 py-1 text-xs rounded {editingPageIndex === pageIndex ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/80'}"
                                    >{page.title || `Page ${pageIndex + 1}`}</button>
                                  {/each}
                                  <button
                                    type="button"
                                    on:click={() => addPage(taskIndex)}
                                    class="px-2 py-1 text-xs border border-dashed border-primary text-primary rounded hover:bg-primary/10"
                                  >+ Page</button>
                                </div>

                                <!-- Current page editor -->
                                {#if editingPageIndex !== null && task.pages[editingPageIndex]}
                                  <div class="space-y-2 p-2 bg-background rounded border border-border">
                                    <div class="flex justify-between items-center">
                                      <input
                                        type="text"
                                        bind:value={task.pages[editingPageIndex].title}
                                        placeholder="Page title"
                                        class="px-2 py-1 text-xs border border-input rounded bg-background w-40"
                                      />
                                      <button
                                        type="button"
                                        on:click={() => removePage(taskIndex, editingPageIndex)}
                                        class="text-xs text-destructive hover:underline"
                                      >Remove Page</button>
                                    </div>

                                    <!-- Blocks -->
                                    <div class="space-y-2">
                                      {#each task.pages[editingPageIndex].blocks as block, blockIndex}
                                        <div class="p-2 border border-border rounded bg-muted/30">
                                          <div class="flex justify-between items-start mb-2">
                                            <span class="text-xs font-medium text-muted-foreground uppercase">{block.type}</span>
                                            <button
                                              type="button"
                                              on:click={() => removeBlock(taskIndex, editingPageIndex, blockIndex)}
                                              class="text-xs text-destructive hover:underline"
                                            >Remove</button>
                                          </div>

                                          {#if block.type === 'text'}
                                            <textarea
                                              value={block.content}
                                              on:input={(e) => updateBlock(taskIndex, editingPageIndex, blockIndex, 'content', e.target.value)}
                                              placeholder="Text content..."
                                              rows="2"
                                              class="w-full px-2 py-1 text-xs border border-input rounded bg-background"
                                            ></textarea>
                                          {:else}
                                            <input
                                              type="text"
                                              value={block.label}
                                              on:input={(e) => updateBlock(taskIndex, editingPageIndex, blockIndex, 'label', e.target.value)}
                                              placeholder="Question label"
                                              class="w-full px-2 py-1 text-xs border border-input rounded bg-background mb-1"
                                            />
                                            <label class="flex items-center gap-1 text-xs mb-1">
                                              <input
                                                type="checkbox"
                                                checked={block.required}
                                                on:change={(e) => updateBlock(taskIndex, editingPageIndex, blockIndex, 'required', e.target.checked)}
                                              />
                                              Required
                                            </label>

                                            {#if block.type === 'multiple_choice' || block.type === 'checkbox'}
                                              <div class="space-y-1 mt-2">
                                                <span class="text-xs text-muted-foreground">Options:</span>
                                                {#each block.options || [] as option, optIndex}
                                                  <div class="flex gap-1">
                                                    <input
                                                      type="text"
                                                      value={option}
                                                      on:input={(e) => updateOption(taskIndex, editingPageIndex, blockIndex, optIndex, e.target.value)}
                                                      class="flex-1 px-2 py-1 text-xs border border-input rounded bg-background"
                                                    />
                                                    <button
                                                      type="button"
                                                      on:click={() => removeOptionFromBlock(taskIndex, editingPageIndex, blockIndex, optIndex)}
                                                      class="text-xs text-destructive px-1"
                                                    >×</button>
                                                  </div>
                                                {/each}
                                                <button
                                                  type="button"
                                                  on:click={() => addOptionToBlock(taskIndex, editingPageIndex, blockIndex)}
                                                  class="text-xs text-primary hover:underline"
                                                >+ Add Option</button>
                                              </div>
                                            {/if}
                                          {/if}
                                        </div>
                                      {/each}
                                    </div>

                                    <!-- Add block buttons -->
                                    <div class="flex flex-wrap gap-1 pt-2">
                                      <span class="text-xs text-muted-foreground mr-1">Add:</span>
                                      <button type="button" on:click={() => addBlock(taskIndex, editingPageIndex, 'text')} class="px-2 py-0.5 text-xs border rounded hover:bg-accent">Text</button>
                                      <button type="button" on:click={() => addBlock(taskIndex, editingPageIndex, 'short_text')} class="px-2 py-0.5 text-xs border rounded hover:bg-accent">Short Answer</button>
                                      <button type="button" on:click={() => addBlock(taskIndex, editingPageIndex, 'long_text')} class="px-2 py-0.5 text-xs border rounded hover:bg-accent">Long Answer</button>
                                      <button type="button" on:click={() => addBlock(taskIndex, editingPageIndex, 'multiple_choice')} class="px-2 py-0.5 text-xs border rounded hover:bg-accent">Multiple Choice</button>
                                      <button type="button" on:click={() => addBlock(taskIndex, editingPageIndex, 'checkbox')} class="px-2 py-0.5 text-xs border rounded hover:bg-accent">Checkboxes</button>
                                      <button type="button" on:click={() => addBlock(taskIndex, editingPageIndex, 'number')} class="px-2 py-0.5 text-xs border rounded hover:bg-accent">Number</button>
                                      <button type="button" on:click={() => addBlock(taskIndex, editingPageIndex, 'audio_recording')} class="px-2 py-0.5 text-xs border rounded hover:bg-accent">Audio Recording</button>
                                    </div>
                                  </div>
                                {/if}
                              </div>
                            {/if}
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </div>
                {:else}
                  <p class="text-xs text-muted-foreground bg-muted/50 p-3 rounded border border-border">
                    Save the study first to add tasks.
                  </p>
                {/if}

                <div class="flex gap-3 justify-end pt-4">
                  <button
                    on:click={() => { showCreateForm = false; resetStudyForm(); }}
                    class="px-4 py-2 border border-input rounded-md text-sm font-medium hover:bg-accent"
                  >Cancel</button>
                  <button
                    on:click={handleCreateOrUpdateStudy}
                    class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90"
                  >{editingStudyId ? 'Update Study' : 'Create Draft'}</button>
                </div>
              </CardContent>
            </Card>
          {:else}
            <!-- Studies List -->
            <div class="mb-4">
              <button
                on:click={() => showCreateForm = true}
                class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90"
              >+ Create New Study</button>
            </div>

            {#if userStudies.length === 0}
              <Card>
                <CardContent class="p-8 text-center">
                  <p class="text-muted-foreground mb-4">You haven't created any studies yet.</p>
                  <p class="text-sm text-muted-foreground">Click "Create New Study" above to get started.</p>
                </CardContent>
              </Card>
            {:else if selectedStudyForRequests}
              <!-- Participation Requests View -->
              <Card>
                <CardHeader>
                  <div class="flex justify-between items-start">
                    <div>
                      <button
                        on:click={closeRequestsView}
                        class="text-sm text-muted-foreground hover:text-foreground mb-2 flex items-center gap-1"
                      >← Back to Studies</button>
                      <CardTitle class="text-lg">Participation Requests</CardTitle>
                      <p class="text-sm text-muted-foreground mt-1">{selectedStudyForRequests.title}</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {#if loadingRequests}
                    <p class="text-muted-foreground text-center py-4">Loading requests...</p>
                  {:else if studyParticipationRequests.length === 0}
                    <p class="text-muted-foreground text-center py-4">No participation requests yet.</p>
                  {:else}
                    <div class="space-y-3">
                      {#each studyParticipationRequests as req}
                        <div class="border border-border rounded-md p-4">
                          <div class="flex justify-between items-start mb-3">
                            <div>
                              <div class="flex items-center gap-2 mb-1">
                                <span class="px-2 py-0.5 rounded text-xs font-medium {getRequestStatusColor(req.status)}">
                                  {req.status}
                                </span>
                                {#if req.consent_acknowledged_at}
                                  <span class="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                    Consent ✓
                                  </span>
                                {:else}
                                  <span class="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                                    No Consent
                                  </span>
                                {/if}
                              </div>
                              <p class="text-xs text-muted-foreground">
                                Requested: {new Date(req.created_at).toLocaleDateString()}
                                {#if req.consent_acknowledged_at}
                                  · Consent: {new Date(req.consent_acknowledged_at).toLocaleDateString()}
                                {/if}
                              </p>
                            </div>
                          </div>

                          <!-- Participant info -->
                          {#if req.user_profiles}
                            <div class="text-sm text-muted-foreground mb-2">
                              <span class="font-medium text-foreground">Participant:</span>
                              {#if req.user_profiles.age}Age {req.user_profiles.age}{/if}
                              {#if req.user_profiles.gender}· {req.user_profiles.gender}{/if}
                              {#if req.user_profiles.zip_code}· ZIP {req.user_profiles.zip_code}{/if}
                            </div>
                            {#if req.user_profiles.conditions && req.user_profiles.conditions.length > 0}
                              <div class="text-xs text-muted-foreground mb-2">
                                Conditions: {req.user_profiles.conditions.join(', ')}
                              </div>
                            {/if}
                          {/if}

                          {#if req.notes}
                            <div class="text-sm bg-muted/50 p-2 rounded mb-3">
                              <span class="font-medium">Note:</span> {req.notes}
                            </div>
                          {/if}

                          <div class="flex gap-2 flex-wrap">
                            {#if req.status === 'pending'}
                              <button
                                on:click={() => handleApproveRequest(req.id)}
                                class="px-3 py-1 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700"
                              >Approve</button>
                              <button
                                on:click={() => handleRejectRequest(req.id)}
                                class="px-3 py-1 bg-red-600 text-white rounded text-xs font-medium hover:bg-red-700"
                              >Reject</button>
                            {/if}
                            {#if req.consent_acknowledged_at}
                              <button
                                on:click={() => handleResetConsent(req.id)}
                                class="px-3 py-1 border border-input rounded text-xs hover:bg-accent"
                              >Reset Consent</button>
                            {/if}
                          </div>
                        </div>
                      {/each}
                    </div>
                  {/if}
                </CardContent>
              </Card>
            {:else if selectedStudyForSubmissions}
              <!-- Task Submissions View -->
              <Card>
                <CardHeader>
                  <div class="flex justify-between items-start">
                    <div>
                      <button
                        on:click={closeSubmissionsView}
                        class="text-sm text-muted-foreground hover:text-foreground mb-2 flex items-center gap-1"
                      >← Back to Studies</button>
                      <CardTitle class="text-lg">Task Submissions</CardTitle>
                      <p class="text-sm text-muted-foreground mt-1">{selectedStudyForSubmissions.title}</p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {#if loadingSubmissions}
                    <p class="text-muted-foreground text-center py-4">Loading submissions...</p>
                  {:else if studyTaskSubmissions.length === 0}
                    <p class="text-muted-foreground text-center py-4">No task submissions yet.</p>
                  {:else}
                    <div class="space-y-3">
                      {#each studyTaskSubmissions as submission}
                        <div class="border border-border rounded-md p-4">
                          <div class="flex justify-between items-start mb-2">
                            <div>
                              <div class="flex items-center gap-2 mb-1">
                                <span class="font-medium text-sm">{getTaskTitle(submission.task_id)}</span>
                              </div>
                              <p class="text-xs text-muted-foreground">
                                Submitted: {new Date(submission.submitted_at).toLocaleString()}
                              </p>
                              <p class="text-xs text-muted-foreground">
                                Participant ID: {submission.user_id.slice(0, 8)}...
                              </p>
                            </div>
                            <button
                              on:click={() => toggleSubmissionExpand(submission.id)}
                              class="px-3 py-1 text-xs border rounded hover:bg-accent"
                            >{expandedSubmissionId === submission.id ? 'Hide' : 'View'} Responses</button>
                          </div>

                          {#if expandedSubmissionId === submission.id}
                            <div class="mt-3 pt-3 border-t border-border space-y-2">
                              {#if submission.responses && typeof submission.responses === 'object'}
                                {#each Object.entries(submission.responses) as [blockId, response]}
                                  <div class="bg-muted/30 p-2 rounded">
                                    <p class="text-xs font-medium text-muted-foreground mb-1">
                                      {getBlockLabel(submission.task_id, blockId)}
                                    </p>
                                    {#if getBlockType(submission.task_id, blockId) === 'audio_recording' && response?.path}
                                      <!-- Audio recording response -->
                                      <div class="space-y-2">
                                        {#await loadAudioUrl(response.path)}
                                          <p class="text-xs text-muted-foreground">Loading audio...</p>
                                        {:then audioUrl}
                                          {#if audioUrl}
                                            <audio controls class="w-full max-w-sm">
                                              <source src={audioUrl} type={response.mimeType || 'audio/webm'} />
                                              Your browser does not support audio playback.
                                            </audio>
                                            <p class="text-xs text-muted-foreground">
                                              Uploaded: {new Date(response.uploadedAt).toLocaleString()} · {Math.round(response.size / 1024)}KB
                                            </p>
                                          {:else}
                                            <p class="text-xs text-destructive">Failed to load audio</p>
                                          {/if}
                                        {/await}
                                      </div>
                                    {:else}
                                      <!-- Regular text response -->
                                      <p class="text-sm">
                                        {#if Array.isArray(response)}
                                          {response.join(', ')}
                                        {:else if typeof response === 'object'}
                                          {JSON.stringify(response)}
                                        {:else}
                                          {response}
                                        {/if}
                                      </p>
                                    {/if}
                                  </div>
                                {/each}
                              {:else}
                                <p class="text-sm text-muted-foreground">No response data</p>
                              {/if}
                            </div>
                          {/if}
                        </div>
                      {/each}
                    </div>

                    <!-- Summary -->
                    <div class="mt-4 pt-4 border-t border-border">
                      <p class="text-sm text-muted-foreground">
                        Total submissions: {studyTaskSubmissions.length}
                      </p>
                    </div>
                  {/if}
                </CardContent>
              </Card>
            {:else}
              {#each userStudies as study}
                <Card>
                  <CardHeader>
                    <div class="flex justify-between items-start">
                      <div class="flex-1">
                        <CardTitle class="text-lg mb-2">
                          {study.title}
                        </CardTitle>
                        <div class="flex items-center gap-2 mb-2">
                          <span class="px-2 py-1 rounded text-xs font-medium {study.is_published ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                            {study.is_published ? 'Published' : 'Draft'}
                          </span>
                          {#if study.recruiting_status}
                            <span class="px-2 py-1 rounded text-xs font-medium bg-primary/10 text-primary">
                              {study.recruiting_status}
                            </span>
                          {/if}
                          <span class="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                            {study.source}
                          </span>
                        </div>
                        {#if study.brief_summary}
                          <p class="text-sm text-muted-foreground line-clamp-2">{study.brief_summary}</p>
                        {/if}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div class="flex justify-between items-center text-sm">
                      <div class="text-muted-foreground">
                        <p>Created: {new Date(study.created_at).toLocaleDateString()}</p>
                        {#if study.conditions && study.conditions.length > 0}
                          <p>Conditions: {study.conditions.slice(0, 3).join(', ')}{study.conditions.length > 3 ? '...' : ''}</p>
                        {/if}
                      </div>
                      <div class="flex gap-2 flex-wrap">
                        <button
                          on:click={() => loadStudyRequests(study)}
                          class="px-3 py-1 border border-primary text-primary rounded-md text-sm hover:bg-primary/10"
                        >Requests</button>
                        <button
                          on:click={() => loadStudySubmissions(study)}
                          class="px-3 py-1 border border-primary text-primary rounded-md text-sm hover:bg-primary/10"
                        >Submissions</button>
                        <button
                          on:click={() => goto(`/study/${study.id}`)}
                          class="px-3 py-1 border border-input rounded-md text-sm hover:bg-accent"
                        >View</button>
                        <button
                          on:click={() => startEditStudy(study)}
                          class="px-3 py-1 border border-input rounded-md text-sm hover:bg-accent"
                        >Edit</button>
                        <button
                          on:click={() => handleTogglePublish(study)}
                          class="px-3 py-1 border border-primary text-primary rounded-md text-sm hover:bg-primary/10"
                        >{study.is_published ? 'Unpublish' : 'Publish'}</button>
                        <button
                          on:click={() => handleDeleteStudy(study.id)}
                          class="px-3 py-1 border border-destructive text-destructive rounded-md text-sm hover:bg-destructive/10"
                        >Delete</button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              {/each}
            {/if}
          {/if}
        </div>
      {/if}

      <!-- Participation Requests Tab -->
      {#if activeTab === 'requests'}
        <div class="space-y-4">
          {#if requests.length === 0}
            <Card>
              <CardContent class="p-8 text-center">
                <p class="text-muted-foreground mb-4">You haven't participated in any studies yet.</p>
                <button
                  on:click={() => goto('/browse')}
                  class="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90"
                >
                  Browse Studies
                </button>
              </CardContent>
            </Card>
          {:else}
            {#each requests as request}
              <Card class="cursor-pointer hover:shadow-md transition-shadow" on:click={() => goto(`/study/${request.study_id}`)}>
                <CardHeader>
                  <div class="flex justify-between items-start">
                    <div class="flex-1">
                      <CardTitle class="text-lg mb-2">
                        {request.studies?.title || 'Study'}
                      </CardTitle>
                      <div class="flex items-center gap-2 mb-2">
                        <span class="px-2 py-1 rounded text-xs font-medium {getStatusColor(request.status)}">
                          {request.status.charAt(0).toUpperCase() + request.status.slice(1)}
                        </span>
                        {#if request.studies?.recruiting_status}
                          <span class="px-2 py-1 rounded text-xs font-medium bg-primary/10 text-primary">
                            {request.studies.recruiting_status}
                          </span>
                        {/if}
                      </div>
                      {#if request.studies?.brief_summary}
                        <p class="text-sm text-muted-foreground line-clamp-2">{request.studies.brief_summary}</p>
                      {/if}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div class="flex justify-between items-center text-sm">
                    <div class="text-muted-foreground">
                      <p>Requested: {new Date(request.created_at).toLocaleDateString()}</p>
                      <p>Contact preference: {request.contact_preference}</p>
                    </div>
                    {#if request.status === 'pending'}
                      <button
                        on:click|stopPropagation={() => handleWithdraw(request.id)}
                        class="px-4 py-2 border border-destructive text-destructive rounded-md text-sm font-medium hover:bg-destructive/10 transition-colors"
                      >
                        Withdraw Request
                      </button>
                    {/if}
                  </div>
                </CardContent>
              </Card>
            {/each}
          {/if}
        </div>
      {/if}

      <!-- Personal Information Tab -->
      {#if activeTab === 'info'}
        <div class="space-y-6">
          <!-- Basic Demographics -->
          <Card>
            <CardHeader>
              <CardTitle>Basic Demographics</CardTitle>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="grid grid-cols-2 gap-4">
                <div class="space-y-2">
                  <label for="age" class="text-sm font-medium">Age</label>
                  <Input
                    id="age"
                    type="number"
                    bind:value={profile.age}
                    placeholder="25"
                  />
                </div>
                <div class="space-y-2">
                  <label for="zip_code" class="text-sm font-medium">ZIP Code</label>
                  <Input
                    id="zip_code"
                    bind:value={profile.zip_code}
                    placeholder="12345"
                    maxlength="5"
                  />
                </div>
              </div>

              <div class="space-y-2">
                <div class="text-sm font-medium">Gender</div>
                <div class="flex gap-4">
                  <label class="flex items-center gap-2">
                    <input type="radio" bind:group={profile.gender} value="male" />
                    <span class="text-sm">Male</span>
                  </label>
                  <label class="flex items-center gap-2">
                    <input type="radio" bind:group={profile.gender} value="female" />
                    <span class="text-sm">Female</span>
                  </label>
                  <label class="flex items-center gap-2">
                    <input type="radio" bind:group={profile.gender} value="other" />
                    <span class="text-sm">Other</span>
                  </label>
                </div>
              </div>
            </CardContent>
          </Card>

          <!-- Medical Conditions -->
          <Card>
            <CardHeader>
              <CardTitle>Medical Conditions</CardTitle>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="space-y-2">
                <div class="text-sm font-medium">Select all conditions that apply</div>
                <div class="grid grid-cols-2 gap-3">
                  {#each conditionOptions as condition}
                    <label class="flex items-center gap-2 p-3 border rounded-md cursor-pointer hover:bg-accent">
                      <input
                        type="checkbox"
                        checked={profile.conditions.includes(condition)}
                        on:change={() => toggleCondition(condition)}
                      />
                      <span class="text-sm">{condition}</span>
                    </label>
                  {/each}
                </div>
              </div>

              {#if profile.conditions.includes('Other')}
                <div class="space-y-2">
                  <label for="other_condition" class="text-sm font-medium">Please specify</label>
                  <Input
                    id="other_condition"
                    bind:value={profile.other_condition}
                    placeholder="Enter condition"
                  />
                </div>
              {/if}
            </CardContent>
          </Card>

          <!-- Current Medications -->
          <Card>
            <CardHeader>
              <CardTitle>Current Medications</CardTitle>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="space-y-2">
                <label for="medications" class="text-sm font-medium">Medications</label>
                <textarea
                  id="medications"
                  bind:value={profile.medications}
                  placeholder="List your current medications (one per line)"
                  rows="4"
                  class="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
                ></textarea>
              </div>

              <div class="space-y-2">
                <label for="allergies" class="text-sm font-medium">Drug Allergies</label>
                <textarea
                  id="allergies"
                  bind:value={profile.allergies}
                  placeholder="List any drug allergies"
                  rows="3"
                  class="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
                ></textarea>
              </div>
            </CardContent>
          </Card>

          <!-- Location & Preferences -->
          <Card>
            <CardHeader>
              <CardTitle>Location & Preferences</CardTitle>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="space-y-2">
                <label for="travel_radius" class="text-sm font-medium">
                  Willing to travel (miles): {profile.travel_radius}
                </label>
                <input
                  id="travel_radius"
                  type="range"
                  bind:value={profile.travel_radius}
                  min="5"
                  max="100"
                  step="5"
                  class="w-full"
                />
                <div class="flex justify-between text-xs text-muted-foreground">
                  <span>5 mi</span>
                  <span>100 mi</span>
                </div>
              </div>

              <div class="space-y-2">
                <div class="text-sm font-medium">Trial Format Preferences</div>
                <label class="flex items-center gap-2 p-3 border rounded-md cursor-pointer">
                  <input type="checkbox" bind:checked={profile.in_person_willing} />
                  <span class="text-sm">Willing to participate in-person</span>
                </label>
                <label class="flex items-center gap-2 p-3 border rounded-md cursor-pointer">
                  <input type="checkbox" bind:checked={profile.remote_willing} />
                  <span class="text-sm">Willing to participate remotely</span>
                </label>
              </div>
            </CardContent>
          </Card>

          <!-- Additional Notes -->
          <Card>
            <CardHeader>
              <CardTitle>Additional Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="space-y-2">
                <label for="additional_notes" class="text-sm font-medium">
                  Additional Notes (Optional)
                </label>
                <textarea
                  id="additional_notes"
                  bind:value={profile.additional_notes}
                  placeholder="Any additional information you'd like to share..."
                  rows="4"
                  class="w-full px-3 py-2 rounded-md border border-input bg-background text-sm"
                ></textarea>
              </div>
            </CardContent>
          </Card>

          <!-- Save Button -->
          <div class="flex justify-end">
            <button
              on:click={saveProfile}
              disabled={saveLoading}
              class="px-6 py-2 bg-primary text-primary-foreground rounded-md font-medium hover:opacity-90 disabled:opacity-50"
            >
              {saveLoading ? 'Saving...' : 'Save Profile'}
            </button>
          </div>
        </div>
      {/if}
    {/if}
  </div>
</main>
