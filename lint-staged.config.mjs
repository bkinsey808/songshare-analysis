const lintStagedConfig = {
	"**/*.{py,md,json,txt}": [
		"prettier --write",
		"git add",
	],
};

export default lintStagedConfig;
