<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { Input } from "$lib/components/ui/input/index.js";
  import { Card, CardHeader, CardTitle, CardContent } from "$lib/components/ui/card/index.js";
  import { user } from '$lib/authStore';
  import { getUserProfile, updateUserProfile, getUserParticipationRequests, withdrawParticipationRequest } from '$lib/supabase';

  let activeTab = 'requests'; // 'requests' or 'info'
  let loading = true;
  let saveLoading = false;
  let requests = [];
  let showSuccessMessage = false;
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
      // Load participation requests
      requests = await getUserParticipationRequests();

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
