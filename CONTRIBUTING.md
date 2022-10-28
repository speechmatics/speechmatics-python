# Contributing

## Developing

To contribute code internally:

- Make sure branches have clear, simple names related to the changes
- Keep the changes as small and modular as possible
- Add all the relevant changes to the unreleased section in the changelog

## Releasing

### From Internal Mirror

To release changes from the internal mirror to public github, follow these steps:

1. Ensure you build the docs with `make docs`
2. Create a separate release MR
3. Update the CHANGELOG, moving unreleased changes to released, and bump VERSION file for your new release
4. Once the release MR is merged, create a tag matching the VERSION. This triggers the auto pipeline that pushes to GitHub
5. This should automatically publish the new docs

### From Public

To release the public changes, create and publish a new release from the new tag. This should automatically trigger a GitHub action.

Note: GitHub workflow runs on `released`. This means it triggers when a release is published, or a pre-release is updated to a release. Drafts will do nothing.