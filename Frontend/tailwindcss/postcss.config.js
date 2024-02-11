import tailwindcss from 'tailwindcss';
import forms from '@tailwindcss/forms';
import typography from '@tailwindcss/typography';
import autoprefixer from 'autoprefixer';

export default {
  plugins: [
    tailwindcss('tailwindcss/tailwind.config.js'),
    forms,
    typography,
    autoprefixer,
  ],
};

