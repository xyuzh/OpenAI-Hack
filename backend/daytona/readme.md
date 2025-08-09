```bash
docker build --platform linux/amd64 -t daytona-fusion-img:6.7 daytona

daytona snapshot push daytona-fusion-img:6.7 -n daytona-fusion-img:6.7 --cpu 4 --disk 10 --memory 8 

daytona snapshot create test --cpu 4 --disk 10 --memory 8 --dockerfile ./daytona/Dockerfile --context ./daytona

daytona snapshot create daytona-fusion-img:4.0 --cpu 4 --disk 10 --memory 8  --dockerfile ./daytona/Dockerfile --context ./daytona/startup.sh

daytona snapshot create 

docker run -it --rm daytona-fusion-img:3.1

docker tag daytona-fusion-img:6.4 xinyzng/fusion:6.4 && docker p
ush xinyzng/fusion:6.4

e2b template build -p daytona
```

```
# Config next js template
RUN mkdir -p /template \
    && bun create next-app /template/nextjs_template --typescript --tailwind --eslint --app --src-dir --turbopack --import-alias "@/*" --use-bun --yes --force \
    && cd /template/nextjs_template \
    && bunx shadcn@latest init --base-color neutral --yes \
    && bunx shadcn@latest add accordion alert alert-dialog aspect-ratio avatar badge breadcrumb button calendar card carousel chart checkbox collapsible command context-menu dialog drawer dropdown-menu form hover-card input input-otp label menubar navigation-menu pagination popover progress radio-group resizable scroll-area select separator sheet sidebar skeleton slider sonner switch table tabs textarea toggle toggle-group tooltip --yes \
    && bun add better-auth @daveyplate/better-auth-ui @prisma/client zod \
    && bun add -d prisma @better-auth/cli autoprefixer \ 
    && bunx prisma init --datasource-provider postgresql \
    && bunx @better-auth/cli generate 

```