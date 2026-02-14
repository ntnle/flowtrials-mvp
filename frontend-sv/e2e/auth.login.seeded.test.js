import { expect, test } from '@playwright/test';

test('seeded researcher can log in', async ({ page }) => {
	await page.goto('/login');

	await page.getByLabel('Email').fill('test@research.edu');
	await page.getByLabel('Password').fill('pass123');
	await page.getByRole('button', { name: 'Log In' }).click();

	// Login page redirects to /browse by default.
	await expect(page).toHaveURL(/\/browse/);

	// Authenticated navbar state.
	await expect(page.getByRole('button', { name: 'Sign Out' })).toBeVisible();

	// Lightweight researcher signal (no deep researcher suite yet).
	await page.goto('/profile');
	await expect(page.getByRole('button', { name: '+ Create New Study' })).toBeVisible();
});
