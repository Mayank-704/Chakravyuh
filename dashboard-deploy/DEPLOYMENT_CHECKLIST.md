# 🚀 Chakravyuh Dashboard - Deployment Checklist

## Pre-Deployment (Development Phase)

- [ ] All dependencies installed: `npm install --legacy-peer-deps`
- [ ] Development server tested: `npm run dev` works on http://localhost:5173
- [ ] API backend running on http://localhost:8000
- [ ] Dashboard connects to backend and fetches data
- [ ] All UI components render correctly
- [ ] Map displays with all nodes visible
- [ ] Terminal panel shows honeypot activity
- [ ] Alert feed populates from API
- [ ] Browser console has no errors

## Build Verification

- [ ] Production build successful: `npm run build`
- [ ] Build creates `dist/` folder with HTML, CSS, JS
- [ ] TypeScript compilation passes with no errors
- [ ] Bundle size is acceptable (~350KB gzipped)
- [ ] All static assets are included
- [ ] Preview mode works: `npm run preview`

## Pre-Production

- [ ] Environment variables configured (.env file)
- [ ] API URL points to production backend
- [ ] CORS headers properly configured on backend
- [ ] SSL/HTTPS certificate ready (if applicable)
- [ ] Security headers configured (CSP, X-Frame-Options, etc.)
- [ ] Authentication/Authorization implemented if needed

## Deployment (Choose One)

### Docker Deployment
- [ ] Dockerfile created and tested locally
- [ ] Docker image builds successfully
- [ ] Container runs and serves dashboard on correct port
- [ ] Port mapping configured correctly
- [ ] Volume mounts set up if needed
- [ ] Environment variables passed to container

### Traditional Server (Nginx/Apache)
- [ ] Server installed and running
- [ ] SSL certificate installed
- [ ] Web server config updated
- [ ] dist/ folder uploaded to correct location
- [ ] File permissions set correctly (644 for files, 755 for dirs)
- [ ] Web server tested and running

### Cloud Platform (Vercel/Netlify/AWS)
- [ ] Repository connected to deployment platform
- [ ] Build settings configured correctly
- [ ] Environment variables set in platform dashboard
- [ ] Build and deploy successful
- [ ] SSL automatically configured
- [ ] Custom domain configured (if applicable)

## Post-Deployment Testing

- [ ] Dashboard accessible at deployment URL
- [ ] Browser console shows no errors
- [ ] API calls successfully fetch data
- [ ] Network requests show 200 status codes
- [ ] Map renders correctly with all nodes
- [ ] Alert feed displays data
- [ ] Metrics cards show correct values
- [ ] Terminal panel updates correctly
- [ ] Page responsive on mobile/tablet
- [ ] Performance metrics acceptable (Lighthouse score > 80)

## Performance & Monitoring

- [ ] Browser DevTools shows fast load time
- [ ] CSS and JS files are compressed/minified
- [ ] No unused CSS or JavaScript in bundle
- [ ] Images optimized and lazy-loaded if applicable
- [ ] API rate limiting configured
- [ ] Error logging/monitoring set up
- [ ] Uptime monitoring configured

## Security Verification

- [ ] HTTPS enforced (redirect http to https)
- [ ] Security headers present:
  - [ ] Content-Security-Policy
  - [ ] X-Frame-Options
  - [ ] X-Content-Type-Options
  - [ ] Strict-Transport-Security
- [ ] No sensitive data in console logs
- [ ] No API keys exposed in frontend code
- [ ] .env file not committed to git
- [ ] Dependencies scanned for vulnerabilities: `npm audit`
- [ ] CORS properly restricts allowed origins

## Backup & Recovery

- [ ] Production backup strategy documented
- [ ] Database backups configured (if applicable)
- [ ] Rollback procedure documented
- [ ] Previous version tag created in git
- [ ] Deployment logs archived

## Documentation

- [ ] README updated with deployment details
- [ ] API endpoint documentation current
- [ ] Environment variables documented
- [ ] Troubleshooting guide completed
- [ ] Team notified of deployment
- [ ] Status page updated

## Go-Live

- [ ] Stakeholders notified
- [ ] Monitoring dashboards set up
- [ ] On-call rotation activated
- [ ] Team ready to respond to issues
- [ ] Production URL communicated to users

---

## Rollback Procedure (If Issues)

1. Stop current deployment
2. Restore previous version
3. Run database migrations backward (if applicable)
4. Verify system health
5. Notify stakeholders

**Estimated Rollback Time**: 5-10 minutes

---

**Deployment Date**: ___________  
**Deployed By**: ___________  
**Version**: 1.0.0  
**Environment**: Production

---

## Notes & Observations

_Document any issues, solutions, or observations during deployment_

```
[Your notes here]
```
