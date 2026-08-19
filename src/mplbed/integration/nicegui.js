export default {
  template: '<div :data-figure-id="figureId"></div>',
  props: {
    figureId: Number,
    websocketUrl: String,
    downloadUrl: String,
  },
  mounted() {
    const pathPrefix = window.path_prefix || "";
    this.figure = window._mpl_webaggext.new_fig(
      this.$el,
      this.figureId,
      pathPrefix + this.websocketUrl,
      pathPrefix + this.downloadUrl,
      "remove",
    );
  },
  beforeUnmount() {
    this.dispose();
  },
  methods: {
    dispose() {
      if (this.figure?.ws) {
        this.figure.ws.close();
        this.figure = undefined;
      }
    },
  },
};
