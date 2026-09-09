import { Layout as RALayout } from "react-admin";
import TopBar from "./TopBar";

// react-admin's core Layout always builds a <Sidebar><Menu/></Sidebar> pair
// to render — a Sidebar that returns null just never mounts it, which is
// what removes the icon rail without losing Layout's other plumbing
// (error boundary, suspense fallback, skip-nav link).
const NoSidebar = () => null;

const AppLayout = (props) => (
  <RALayout
    {...props}
    appBar={TopBar}
    sidebar={NoSidebar}
    sx={{
      "& .RaLayout-content": {
        padding: { xs: "16px 16px 32px", md: "20px 24px 40px" },
        maxWidth: "100%",
        overflowX: "hidden",
      },
      "& .RaLayout-appFrame": {
        marginTop: "48px !important",
      },
      "& .RaLayout-contentWrapper": { marginLeft: 0 },
      "& .RaList-actions": { minHeight: 0, margin: 0 },
      "& .RaList-content": { overflow: "hidden" },
      "& .MuiTableContainer-root, & .RaDatagrid-tableWrapper": {
        overflowX: "auto",
      },
      "& .MuiTable-root": {
        minWidth: 880,
      },
      "& .RaShow-main": { maxWidth: "100%" },
      "& .RaShow-card": {
        boxShadow: "none",
        backgroundImage: "none",
        backgroundColor: "transparent",
        overflow: "visible",
      },
      "& .RaSimpleShowLayout-root": {
        display: "grid !important",
        gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
        columnGap: 3,
        rowGap: 2,
        paddingTop: 1,
      },
      "& .RaSimpleShowLayout-stack": { display: "contents" },
      "& pre": {
        margin: 0,
        maxWidth: "100%",
        maxHeight: 360,
        overflow: "auto",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        fontSize: 13,
        lineHeight: 1.5,
        background: "#F4F5FC",
        borderRadius: 8,
        padding: 12,
      },
    }}
  />
);

export default AppLayout;
