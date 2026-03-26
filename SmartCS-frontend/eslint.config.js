import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import vueTsEslintConfig from "@vue/eslint-config-typescript";

export default [
  {
    ignores: ["dist", "node_modules"]
  },
  js.configs.recommended,
  ...pluginVue.configs["flat/recommended"],
  ...vueTsEslintConfig()
];
