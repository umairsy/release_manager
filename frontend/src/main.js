import { createApp } from "vue";
import { Badge, Button, FormControl, FrappeUI, frappeRequest, setConfig } from "frappe-ui";
import App from "./App.vue";
import { router } from "./router";
import "./index.css";

setConfig("resourceFetcher", frappeRequest);

const app = createApp(App);
app.use(FrappeUI);
app.use(router);
app.component("Button", Button);
app.component("Badge", Badge);
app.component("FormControl", FormControl);
app.mount("#app");
