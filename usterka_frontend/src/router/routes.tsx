import { lazy, Suspense, type ReactNode } from 'react';
import type { RouteObject } from 'react-router-dom';
import AuthLayout from 'src/layouts/AuthLayout';
import MainLayout from 'src/layouts/MainLayout';
import RequireAuth from './RequireAuth';

const LoginPage = lazy(() => import('src/pages/LoginPage'));
const ProjectListPage = lazy(() => import('src/pages/ProjectListPage'));
const ProjectPage = lazy(() => import('src/pages/ProjectPage'));
const PlanPage = lazy(() => import('src/pages/PlanPage'));
const SubscriptionPage = lazy(() => import('src/pages/SubscriptionPage'));
const LandingPage = lazy(() => import('src/pages/LandingPage'));
const SettingsPage = lazy(() => import('src/pages/SettingsPage'));
const ErrorNotFound = lazy(() => import('src/pages/ErrorNotFound'));

const page = (el: ReactNode) => <Suspense fallback={null}>{el}</Suspense>;

/** Trasy wzorem lol_spy/router/routes.js: chronione w MainLayout, logowanie w AuthLayout. */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <RequireAuth><MainLayout /></RequireAuth>,
    children: [
      { index: true, element: page(<ProjectListPage />) },
      { path: 'projects/:projectId', element: page(<ProjectPage />) },
      { path: 'projects/:projectId/plans/:planId', element: page(<PlanPage />) },
      { path: 'subscription', element: page(<SubscriptionPage />) },
      { path: 'settings', element: page(<SettingsPage />) },
    ],
  },
  { path: '/welcome', element: page(<LandingPage />) },
  { path: '/login', element: <AuthLayout />, children: [{ index: true, element: page(<LoginPage />) }] },
  { path: '*', element: page(<ErrorNotFound />) },
];
