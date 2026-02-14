import { expect, test } from '@playwright/test';

test('signup works and profile can be saved', async ({ page }) => {
	const uniqueEmail = `e2e+${Date.now()}@example.com`;
	const password = 'pass1234';

	await page.goto('/signup');

	await page.getByLabel('Email').fill(uniqueEmail);
	await page.getByLabel('Password').fill(password);
	await page.getByLabel('Confirm Password').fill(password);

	// Consent is required to submit.
	await page.getByRole('checkbox').check();

	await page.getByRole('button', { name: 'Create Profile & Continue' }).click();

	// Signup redirects to /profile when confirmations are disabled.
	await expect(page).toHaveURL(/\/profile/);
	await expect(page.getByRole('heading', { name: 'Manage Your Participation' })).toBeVisible();

	// Fill the minimal profile fields.
	await page.getByRole('button', { name: 'Personal Information' }).click();
	await page.getByLabel('Age').fill('25');
	await page.getByLabel('ZIP Code').fill('02139');
	await page.getByLabel('Male').check();

	// Saving profile shows a browser alert.
	page.once('dialog', async (dialog) => {
		expect(dialog.message()).toBe('Profile saved successfully!');
		await dialog.accept();
	});

	await page.getByRole('button', { name: 'Save Profile' }).click();

	// Quick persistence check (reload and re-assert values).
	await page.reload();
	await page.getByRole('button', { name: 'Personal Information' }).click();
	await expect(page.getByLabel('Age')).toHaveValue('25');
	await expect(page.getByLabel('ZIP Code')).toHaveValue('02139');
});
