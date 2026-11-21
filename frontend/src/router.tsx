// Import QueryClient from TanStack Query for client-side asynchronous caching and state management
import { QueryClient } from "@tanstack/react-query";
// Import createRouter from TanStack Router to instantiate the client router
import { createRouter } from "@tanstack/react-router";
// Import automatically generated route tree mapping all application routes
import { routeTree } from "./routeTree.gen";

// Define and export factory function to construct a fresh router instance
export const getRouter = () => {
  // Instantiate a new QueryClient instance for caching requests
  const queryClient = new QueryClient();

  // Create TanStack Router instance with route tree and configuration options
  const router = createRouter({
    // Attach the generated route tree
    routeTree,
    // Provide dependency injection context including queryClient
    context: { queryClient },
    // Enable automatic browser window scroll position restoration upon navigation
    scrollRestoration: true,
    // Set stale time for preloaded routes to 0 for immediate fresh fetches
    defaultPreloadStaleTime: 0,
  });

  // Return configured router instance
  return router;
};
