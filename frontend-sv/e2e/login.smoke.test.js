import { expect, test } from '@playwright/test';

test('login page renders inside app shell', async ({ page }) => {
	await page.goto('/login');

	// The (app) route group always renders the navbar.
	await expect(page.locator('nav')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Flow Trials' })).toBeVisible();

	// Wait for auth hydration to complete so the unauthenticated actions appear.
	await expect(page.getByRole('link', { name: 'Login' })).toBeVisible();
	await expect(page.getByRole('link', { name: 'Sign Up' })).toBeVisible();

	// Login form content.
	await expect(page.getByRole('heading', { name: 'Log In' })).toBeVisible();
	await expect(page.getByLabel('Email')).toBeVisible();
	await expect(page.getByLabel('Password')).toBeVisible();
	await expect(page.getByRole('button', { name: 'Log In' })).toBeVisible();
});
