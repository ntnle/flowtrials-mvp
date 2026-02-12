import { expect, test } from '@playwright/test';

test('focused join page has no navbar', async ({ page }) => {
	// The join route calls FastAPI GET /studies/:id via $lib/api.js.
	// Stub it so this test doesn't depend on the backend being up.
	await page.route('**/studies/123', async (route) => {
		await route.fulfill({
			status: 200,
			contentType: 'application/json',
			body: JSON.stringify({
				id: 123,
				title: 'Test Joinable Study',
				join_flow_key: 'koreng_phoneme'
			})
		});
	});

	await page.goto('/join/123');

	// (focus) routes should not render the global app navbar.
	await expect(page.locator('nav')).toHaveCount(0);

	// Page content should render once auth hydration is done.
	await expect(page.getByRole('heading', { name: 'Test Joinable Study' })).toBeVisible();
	await expect(page.getByText('Step 1 of 4')).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Create your account' })).toBeVisible();
});
