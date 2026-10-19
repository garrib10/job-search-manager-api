// Railway Infrastructure as Code for the API service.
//
// Preview changes:  railway config plan     (read-only)
// Apply them:       railway config apply
//
// Safety:
// - `partial` limits this file to the API service. Without it, resources not
//   declared here (such as the MySQL database) would be deleted on apply.
// - `variables.managed: false` keeps environment variables and secrets in
//   Railway, out of this file.
//
// See docs/design-decisions.md and https://docs.railway.com/infrastructure-as-code
import { defineRailway, github, project, service } from "railway/iac";
// This repository manages only its own resources in the environment. Other
// repositories export their own partial name.
// See https://docs.railway.com/infrastructure-as-code#multi-repo-projects
export const partial = "job-search-manager-api";
export default defineRailway(() => {
  const jobSearchManagerApi = service("job-search-manager-api", {
    source: github("garrib10/job-search-manager-api", { branch: "main", checkSuites: false }),
    build: { buildEnvironment: "V3", builder: "RAILPACK" },
    start: "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    healthcheck: "/health",
    preDeploy: "alembic upgrade head",
    replicas: { "sfo": 1 },
    deploy: { preDeployTimeoutSeconds: 300, sleepApplication: true },
  });

  return project("Job-Search-Manager-Api", {
    variables: { managed: false },
    resources: [jobSearchManagerApi],
  });
});
