# Aria GitHub Pages

This directory contains the GitHub Pages website for Aria, a powerful, self-hosted AI assistant.

## Setting Up GitHub Pages

To enable GitHub Pages for this repository:

1. Go to the repository settings on GitHub
2. Scroll down to the "GitHub Pages" section
3. Under "Source", select the branch where your docs directory is located (e.g., `main`)
4. Select the `/docs` folder as the source
5. Click "Save"

Your site will be published at `https://username.github.io/aria/` (replace `username` with your GitHub username).

## Local Development

To test the site locally:

1. Install Jekyll and Bundler:
   ```
   gem install jekyll bundler
   ```

2. Navigate to the `docs` directory:
   ```
   cd docs
   ```

3. Create a Gemfile:
   ```
   echo "source 'https://rubygems.org'" > Gemfile
   echo "gem 'github-pages', group: :jekyll_plugins" >> Gemfile
   ```

4. Install dependencies:
   ```
   bundle install
   ```

5. Run the local server:
   ```
   bundle exec jekyll serve
   ```

6. Open your browser and go to `http://localhost:4000`

## Structure

- `_config.yml`: Jekyll configuration
- `_layouts/`: Custom layouts
- `_includes/`: Reusable components
- `assets/`: Static assets (CSS, images, etc.)
- `*.md`: Content pages in Markdown format

## Customization

To customize the site:

- Edit `_config.yml` to change site-wide settings
- Modify files in `_layouts/` and `_includes/` to change the structure
- Update CSS in `assets/css/` to change the appearance
- Edit Markdown files to update content
