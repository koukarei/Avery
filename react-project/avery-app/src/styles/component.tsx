import { StyleSheet } from 'react-native'

const styles = StyleSheet.create({
    App: {
        textAlign: 'center',
        backgroundColor: 'background.default', 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'text.primary',
        position: 'relative',
    },
    BackgroundStyle: {
        height: '100%',
        width: '100%',
        backgroundColor: 'black',

    },
    BackgroundSpotlight:{
        position: 'absolute',
        width: 100,
        height: 100,
        color: 'white',
    }
});

export default styles